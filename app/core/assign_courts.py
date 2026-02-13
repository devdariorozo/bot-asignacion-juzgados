import os
import time
import hashlib
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from geopy.distance import geodesic
from typing import Optional

load_dotenv()

# Configuración de BD y funciones de API
from app.utils.database import DB_NAMES, get_database_url
from app.utils.google_api import geocode_address_with_logging, get_distance_matrix_with_logging
from app.utils.city_variants import cities_match, get_city_search_variants


def calculate_client_hash(lawsuit_id, address, neighborhood, city, department, type_quantity):
    """Calcula hash para el cliente"""
    data_string = (
        f"{lawsuit_id}|"
        f"{address or ''}|"
        f"{neighborhood or ''}|"
        f"{city or ''}|"
        f"{department or ''}|"
        f"{type_quantity or ''}"
    )
    return hashlib.sha256(data_string.encode('utf-8')).hexdigest()


def process_pending_lawsuits_single_db(db_name: str, limit: Optional[int] = None):
    """
    Procesa demandas pendientes y asigna/actualiza juzgados para UNA base de datos
    
    Args:
        db_name: Nombre de la base de datos
        limit: Número máximo de demandas a procesar (None = todas)
    
    Returns:
        dict: Estadísticas del procesamiento
    """
    from app.bot_control import BotController
    
    print("\n" + "=" * 70)
    print(f"⚙️ PROCESANDO ASIGNACIONES - BD: {db_name}")
    print("=" * 70)
    
    BotController.log(f"⚙️ Iniciando procesamiento de asignaciones - BD: {db_name}", "INFO")
    
    database_url = get_database_url(db_name)
    engine = create_engine(database_url, echo=False)
    
    with engine.connect() as connection:
        
        # Obtener demandas activas y pendientes
        query = """
            SELECT 
                l.id as lawsuit_id,
                l.client_id,
                l.type_quantity,
                c.identification,
                a.adress,
                a.neighborhood,
                vc.city_name as city,
                vc.department as department
            FROM lawsuits l
            INNER JOIN clients c ON l.client_id = c.id
            LEFT JOIN adresses a ON c.id = a.client_id 
                AND a.deleted_at IS NULL
                AND a.is_active = 1
                AND a.id = (
                    SELECT MIN(id)
                    FROM adresses
                    WHERE client_id = c.id
                    AND deleted_at IS NULL
                    AND is_active = 1
                )
            LEFT JOIN v_cities vc ON a.city_id = vc.id
            WHERE l.lawsuit_status = 'Pendiente'
            AND l.deleted_at IS NULL
            AND c.deleted_at IS NULL
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        result = connection.execute(text(query))
        lawsuits = result.fetchall()
        
        if not lawsuits:
            print("\n✅ No hay demandas pendientes para procesar")
            BotController.log(f"✅ [{db_name}] No hay demandas pendientes", "INFO")
            return {
                "db_name": db_name,
                "total_procesados": 0,
                "success": 0,
                "no_address": 0,
                "no_court_in_city": 0,
                "wrong_city": 0,
                "error": 0,
                "updated": 0,
                "inserted": 0,
                "skipped": 0,
                "api_calls_saved": 0
            }
        
        print(f"\n📋 Demandas a procesar: {len(lawsuits)}")
        BotController.log(f"📋 [{db_name}] Procesando {len(lawsuits)} demandas", "INFO")
        print("=" * 70)
        
        success_count = 0
        no_address_count = 0
        no_court_in_city_count = 0
        wrong_city_count = 0
        error_count = 0
        updated_count = 0
        inserted_count = 0
        skipped_count = 0
        api_calls_saved_count = 0
        
        for i, lawsuit in enumerate(lawsuits, 1):
            lawsuit_id = lawsuit[0]
            client_id = lawsuit[1]
            type_quantity = lawsuit[2]
            client_identification = lawsuit[3]
            client_address = lawsuit[4]
            client_neighborhood = lawsuit[5]
            client_city = lawsuit[6]
            client_department = lawsuit[7]
            
            print(f"\n[{i}/{len(lawsuits)}] Cliente: {client_identification} (Lawsuit ID: {lawsuit_id}, Client ID: {client_id})")
            print(f"   Tipo cuantía: {type_quantity}")
            print(f"   Ciudad: {client_city or 'N/A'}")
            
            # Calcular hash y verificar si cambió
            current_hash = calculate_client_hash(
                lawsuit_id,
                client_address,
                client_neighborhood,
                client_city,
                client_department,
                type_quantity
            )
            
            # Verificar si ya existe registro
            check_query = text("""
                SELECT id, data_hash, court_name 
                FROM lawsuit_court_assignments 
                WHERE client_id = :client_id
            """)
            existing = connection.execute(check_query, {"client_id": client_id}).fetchone()
            
            if existing:
                existing_id = existing[0]
                stored_hash = existing[1]
                existing_court = existing[2]
                
                # Solo omitir si el hash es igual Y tiene juzgado asignado válido
                if stored_hash == current_hash and existing_court and existing_court not in [
                    "Sin dirección",
                    "Error en geocodificación",
                    "Dirección incorrecta o en otra ciudad",
                    "No se encuentra juzgado en ciudad"
                ]:
                    BotController.log(
                        f"⏭️ [{db_name}] Cliente {client_identification} sin cambios - Omitido",
                        "INFO"
                    )
                    skipped_count += 1
                    continue
                
                # Si el hash NO cambió Y tiene "No se encuentra juzgado en ciudad"
                # Verificar si AHORA sí hay juzgados disponibles
                if stored_hash == current_hash and existing_court == "No se encuentra juzgado en ciudad":
                    # Validar que tenga dirección y ciudad
                    if not client_address or not client_city:
                        skipped_count += 1
                        continue
                    
                    # 🔥 CAMBIO: Buscar con variantes de ciudad
                    search_cities = get_city_search_variants(client_city)
                    
                    # Construir query con OR para múltiples variantes
                    city_conditions = " OR ".join([f"UPPER(TRIM(dc.city)) = :city{idx}" for idx in range(len(search_cities))])
                    
                    courts_check_query = text(f"""
                        SELECT COUNT(*) 
                        FROM data_courts dc
                        INNER JOIN court_coordinates cc ON dc.id = cc.court_id
                        WHERE dc.status = 'Activo'
                        AND dc.deleted_at IS NULL
                        AND cc.deleted_at IS NULL
                        AND dc.type_cuantity = :cuantia
                        AND ({city_conditions})
                    """)
                    
                    # Construir parámetros dinámicos
                    params = {"cuantia": type_quantity}
                    for idx, city_variant in enumerate(search_cities):
                        params[f"city{idx}"] = city_variant
                    
                    result_check = connection.execute(courts_check_query, params)
                    courts_available = result_check.fetchone()[0]
                    
                    # Si no hay juzgados - omitir la llamada a la API
                    if courts_available == 0:
                        print(f"   ⏭️  Sigue sin haber juzgados en {client_city} - Omitiendo (ahorrando API)")
                        BotController.log(
                            f"💰 [{db_name}] Cliente {client_identification} - Sin juzgados en {client_city} - 2 llamadas API ahorradas",
                            "INFO"
                        )
                        skipped_count += 1
                        api_calls_saved_count += 2
                        continue
                    else:
                        # Si hay juzgados - llamar a la api
                        print(f"   🔄 Ahora SÍ hay juzgados en {client_city} ({courts_available} disponibles) - Reintentando asignación")
                        BotController.log(
                            f"🔄 [{db_name}] Cliente {client_identification} - Detectados {courts_available} juzgados nuevos en {client_city} - Reintentando",
                            "INFO"
                        )
                
                # En cualquier otro caso, actualizar
                if existing_court in [
                    "Sin dirección",
                    "Error en geocodificación",
                    "Dirección incorrecta o en otra ciudad"
                ] and stored_hash == current_hash:
                    print(f"   🔄 Actualizando registro existente (ID: {existing_id}) - Datos cambiaron o reintentando")
                else:
                    print(f"   🔄 Actualizando registro existente (ID: {existing_id})")
            else:
                print(f"   🆕 Creando nuevo registro")
            
            # Validar que tenga dirección y ciudad
            if not client_address or not client_city:
                print(f"   ⚠️  Sin dirección válida")
                
                if existing:
                    update_query = text("""
                        UPDATE lawsuit_court_assignments
                        SET lawsuit_id = :lawsuit_id,
                            client_identification = :identification,
                            client_address = :address,
                            client_city = :city,
                            court_id = NULL,
                            court_name = :message,
                            distance_km = NULL,
                            cuantia_type = NULL,
                            data_hash = :hash,
                            updated_at = NOW()
                        WHERE client_id = :client_id
                    """)
                    connection.execute(update_query, {
                        "lawsuit_id": lawsuit_id,
                        "client_id": client_id,
                        "identification": client_identification,
                        "address": "Sin dirección",
                        "city": client_city or "N/A",
                        "message": "Sin dirección",
                        "hash": current_hash
                    })
                    updated_count += 1
                else:
                    insert_query = text("""
                        INSERT INTO lawsuit_court_assignments 
                        (lawsuit_id, client_id, client_identification, client_address, 
                         client_city, court_name, distance_km, data_hash)
                        VALUES (:lawsuit_id, :client_id, :identification, :address, 
                                :city, :message, NULL, :hash)
                    """)
                    connection.execute(insert_query, {
                        "lawsuit_id": lawsuit_id,
                        "client_id": client_id,
                        "identification": client_identification,
                        "address": "Sin dirección",
                        "city": client_city or "N/A",
                        "message": "Sin dirección",
                        "hash": current_hash
                    })
                    inserted_count += 1
                
                connection.commit()
                no_address_count += 1
                continue
            
            # Geocodificar dirección del cliente
            full_address = f"{client_address}, {client_neighborhood or ''}, {client_city}"
            print(f"   📍 Geocodificando: {full_address}")
            
            client_lat, client_lng, found_city = geocode_address_with_logging(
                client_address,
                client_city,
                client_department,
                client_neighborhood,
                db_name=db_name
            )
            
            if not client_lat or not client_lng:
                print(f"   ❌ Error al geocodificar")
                
                if existing:
                    update_query = text("""
                        UPDATE lawsuit_court_assignments
                        SET lawsuit_id = :lawsuit_id,
                            client_identification = :identification,
                            client_address = :address,
                            client_city = :city,
                            court_id = NULL,
                            court_name = :message,
                            distance_km = NULL,
                            cuantia_type = NULL,
                            data_hash = :hash,
                            updated_at = NOW()
                        WHERE client_id = :client_id
                    """)
                    connection.execute(update_query, {
                        "lawsuit_id": lawsuit_id,
                        "client_id": client_id,
                        "identification": client_identification,
                        "address": full_address,
                        "city": client_city,
                        "message": "Error en geocodificación",
                        "hash": current_hash
                    })
                    updated_count += 1
                else:
                    insert_query = text("""
                        INSERT INTO lawsuit_court_assignments 
                        (lawsuit_id, client_id, client_identification, client_address, 
                         client_city, court_name, distance_km, data_hash)
                        VALUES (:lawsuit_id, :client_id, :identification, :address, 
                                :city, :message, NULL, :hash)
                    """)
                    connection.execute(insert_query, {
                        "lawsuit_id": lawsuit_id,
                        "client_id": client_id,
                        "identification": client_identification,
                        "address": full_address,
                        "city": client_city,
                        "message": "Error en geocodificación",
                        "hash": current_hash
                    })
                    inserted_count += 1
                
                connection.commit()
                error_count += 1
                continue
            
            print(f"   ✅ Coordenadas: ({client_lat}, {client_lng})")
            print(f"   🏙️  Ciudad encontrada: {found_city or 'N/A'}")
            
            #alidar que la dirección esté en la ciudad correcta usando cities_match()
            if found_city:
                if not cities_match(found_city, client_city):
                    print(f"   ⚠️  Dirección geocodificada en ciudad diferente")
                    print(f"       Esperada: {client_city}")
                    print(f"       Encontrada: {found_city}")
                    
                    if existing:
                        update_query = text("""
                            UPDATE lawsuit_court_assignments
                            SET lawsuit_id = :lawsuit_id,
                                client_identification = :identification,
                                client_address = :address,
                                client_city = :city,
                                court_id = NULL,
                                court_name = :message,
                                distance_km = NULL,
                                cuantia_type = NULL,
                                data_hash = :hash,
                                updated_at = NOW()
                            WHERE client_id = :client_id
                        """)
                        connection.execute(update_query, {
                            "lawsuit_id": lawsuit_id,
                            "client_id": client_id,
                            "identification": client_identification,
                            "address": f"Dirección en {found_city}, no en {client_city}",
                            "city": client_city,
                            "message": "Dirección incorrecta o en otra ciudad",
                            "hash": current_hash
                        })
                        updated_count += 1
                    else:
                        insert_query = text("""
                            INSERT INTO lawsuit_court_assignments 
                            (lawsuit_id, client_id, client_identification, client_address, 
                             client_city, court_name, distance_km, data_hash)
                            VALUES (:lawsuit_id, :client_id, :identification, :address, 
                                    :city, :message, NULL, :hash)
                        """)
                        connection.execute(insert_query, {
                            "lawsuit_id": lawsuit_id,
                            "client_id": client_id,
                            "identification": client_identification,
                            "address": f"Dirección en {found_city}, no en {client_city}",
                            "city": client_city,
                            "message": "Dirección incorrecta o en otra ciudad",
                            "hash": current_hash
                        })
                        inserted_count += 1
                    
                    connection.commit()
                    wrong_city_count += 1
                    continue
            
            #Buscar juzgados con variantes de ciudad
            search_cities = get_city_search_variants(client_city)

            city_conditions = " OR ".join([f"UPPER(TRIM(dc.city)) = :city{idx}" for idx in range(len(search_cities))])
            
            courts_query = text(f"""
                SELECT 
                    dc.id,
                    dc.name,
                    dc.adress,
                    dc.city,
                    dc.type_cuantity,
                    cc.latitude,
                    cc.longitude
                FROM data_courts dc
                INNER JOIN court_coordinates cc ON dc.id = cc.court_id
                WHERE dc.status = 'Activo'
                AND dc.deleted_at IS NULL
                AND cc.deleted_at IS NULL
                AND dc.type_cuantity = :cuantia
                AND ({city_conditions})
            """)
            
            # Construir parámetros dinámicos
            params = {"cuantia": type_quantity}
            for idx, city_variant in enumerate(search_cities):
                params[f"city{idx}"] = city_variant
            
            result = connection.execute(courts_query, params)
            courts = result.fetchall()
            
            if not courts:
                print(f"   ⚠️  No hay juzgados de '{type_quantity}' en {client_city}")
                
                if existing:
                    update_query = text("""
                        UPDATE lawsuit_court_assignments
                        SET lawsuit_id = :lawsuit_id,
                            client_identification = :identification,
                            client_address = :address,
                            client_city = :city,
                            court_id = NULL,
                            court_name = :message,
                            distance_km = NULL,
                            cuantia_type = :cuantia,
                            data_hash = :hash,
                            updated_at = NOW()
                        WHERE client_id = :client_id
                    """)
                    connection.execute(update_query, {
                        "lawsuit_id": lawsuit_id,
                        "client_id": client_id,
                        "identification": client_identification,
                        "address": full_address,
                        "city": client_city,
                        "message": "No se encuentra juzgado en ciudad",
                        "cuantia": type_quantity,
                        "hash": current_hash
                    })
                    updated_count += 1
                else:
                    insert_query = text("""
                        INSERT INTO lawsuit_court_assignments 
                        (lawsuit_id, client_id, client_identification, client_address, 
                         client_city, court_name, distance_km, cuantia_type, data_hash)
                        VALUES (:lawsuit_id, :client_id, :identification, :address, 
                                :city, :message, NULL, :cuantia, :hash)
                    """)
                    connection.execute(insert_query, {
                        "lawsuit_id": lawsuit_id,
                        "client_id": client_id,
                        "identification": client_identification,
                        "address": full_address,
                        "city": client_city,
                        "message": "No se encuentra juzgado en ciudad",
                        "cuantia": type_quantity,
                        "hash": current_hash
                    })
                    inserted_count += 1
                
                connection.commit()
                no_court_in_city_count += 1
                continue
            
            print(f"   🏛️  Juzgados encontrados en {client_city}: {len(courts)}")
            
            # Calcular distancias en línea recta
            courts_with_distance = []
            
            for court in courts:
                court_id = court[0]
                court_name = court[1]
                court_lat = float(court[5])
                court_lng = float(court[6])
                
                distance = geodesic(
                    (client_lat, client_lng),
                    (court_lat, court_lng)
                ).kilometers
                
                courts_with_distance.append({
                    'court_id': court_id,
                    'court_name': court_name,
                    'lat': court_lat,
                    'lng': court_lng,
                    'straight_distance': distance
                })
            
            courts_with_distance.sort(key=lambda x: x['straight_distance'])
            top_courts = courts_with_distance[:5]

            # Calcular distancias reales con logging
            destinations = [
                (c['lat'], c['lng'], c['court_id'], c['court_name'])
                for c in top_courts
            ]
            
            real_distances = get_distance_matrix_with_logging(
                client_lat, 
                client_lng, 
                destinations,
                db_name=db_name
            )
            
            if not real_distances:
                print(f"   ⚠️  Error al calcular distancias reales, usando línea recta")
                closest_court = top_courts[0]
                final_distance = closest_court['straight_distance']
            else:
                closest_court_data = real_distances[0]
                closest_court = next(
                    c for c in top_courts
                    if c['court_id'] == closest_court_data['court_id']
                )
                final_distance = closest_court_data['distance_km']
            
            # Guardar asignación de juzgado
            print(f"   ✅ Juzgado asignado: {closest_court['court_name']}")
            print(f"   📏 Distancia: {final_distance:.2f} km")
            
            if existing:
                update_query = text("""
                    UPDATE lawsuit_court_assignments
                    SET lawsuit_id = :lawsuit_id,
                        client_identification = :identification,
                        client_address = :client_address,
                        client_city = :client_city,
                        court_id = :court_id,
                        court_name = :court_name,
                        distance_km = :distance,
                        cuantia_type = :cuantia,
                        data_hash = :hash,
                        updated_at = NOW()
                    WHERE client_id = :client_id
                """)
                connection.execute(update_query, {
                    "lawsuit_id": lawsuit_id,
                    "client_id": client_id,
                    "identification": client_identification,
                    "client_address": full_address,
                    "client_city": client_city,
                    "court_id": closest_court['court_id'],
                    "court_name": closest_court['court_name'],
                    "distance": final_distance,
                    "cuantia": type_quantity,
                    "hash": current_hash
                })
                updated_count += 1
            else:
                insert_query = text("""
                    INSERT INTO lawsuit_court_assignments 
                    (lawsuit_id, client_id, client_identification, client_address, 
                     client_city, court_id, court_name, distance_km, cuantia_type, data_hash)
                    VALUES (:lawsuit_id, :client_id, :identification, :client_address, 
                            :client_city, :court_id, :court_name, :distance, :cuantia, :hash)
                """)
                connection.execute(insert_query, {
                    "lawsuit_id": lawsuit_id,
                    "client_id": client_id,
                    "identification": client_identification,
                    "client_address": full_address,
                    "client_city": client_city,
                    "court_id": closest_court['court_id'],
                    "court_name": closest_court['court_name'],
                    "distance": final_distance,
                    "cuantia": type_quantity,
                    "hash": current_hash
                })
                inserted_count += 1
            
            connection.commit()
            success_count += 1
            time.sleep(0.1)

        print("\n" + "=" * 70)
        print(f"📊 RESUMEN - BD: {db_name}")
        print("=" * 70)
        print(f"✅ Juzgados asignados: {success_count}")
        print(f"🔄 Registros actualizados: {updated_count}")
        print(f"🆕 Registros nuevos: {inserted_count}")
        print(f"⏭️  Registros omitidos (sin cambios): {skipped_count}")
        print(f"⚠️  Sin dirección: {no_address_count}")
        print(f"⚠️  Dirección en ciudad incorrecta: {wrong_city_count}")
        print(f"⚠️  Sin juzgado en ciudad: {no_court_in_city_count}")
        print(f"❌ Errores: {error_count}")
        print(f"📋 Total procesados: {len(lawsuits)}")
        print(f"💰 Llamadas API ahorradas (hash): ~{(skipped_count - api_calls_saved_count) * 2}")
        print(f"💰 Llamadas API ahorradas (sin juzgados): {api_calls_saved_count}")
        print(f"💰 TOTAL llamadas API ahorradas: ~{(skipped_count * 2) + api_calls_saved_count}")
        print("=" * 70)
        
        BotController.log(
            f"✅ [{db_name}] Procesamiento completado - "
            f"Asignados: {success_count}, Omitidos: {skipped_count}, "
            f"API ahorradas: {(skipped_count * 2) + api_calls_saved_count}",
            "INFO"
        )
        
        return {
            "db_name": db_name,
            "total_procesados": len(lawsuits),
            "success": success_count,
            "no_address": no_address_count,
            "no_court_in_city": no_court_in_city_count,
            "wrong_city": wrong_city_count,
            "error": error_count,
            "updated": updated_count,
            "inserted": inserted_count,
            "skipped": skipped_count,
            "api_calls_saved": api_calls_saved_count
        }


def process_pending_lawsuits(limit: Optional[int] = None):
    """
    Procesa demandas pendientes en TODAS las bases de datos configuradas
    
    Args:
        limit: Número máximo de demandas a procesar por BD (None = todas)
    """
    from app.bot_control import BotController

    print("🚀 INICIANDO PROCESAMIENTO MULTI-BASE DE DATOS")
    
    BotController.log(f"🚀 Iniciando procesamiento en {len(DB_NAMES)} bases de datos", "INFO")
    
    results = []
    
    for i, db_name in enumerate(DB_NAMES, 1):
        print(f"📦 BASE DE DATOS {i}/{len(DB_NAMES)}: {db_name}")
        
        try:
            result = process_pending_lawsuits_single_db(db_name, limit)
            results.append(result)
        except Exception as e:
            error_msg = str(e)
            BotController.log(f"❌ Error en BD {db_name}: {error_msg}", "ERROR")
            print(f"\n❌ ERROR: {error_msg}")
            results.append({
                "db_name": db_name,
                "error": error_msg,
                "total_procesados": 0,
                "success": 0,
                "api_calls_saved": 0
            })
    
    # Resumen de todo
    print("📊 RESUMEN GLOBAL DE PROCESAMIENTO")
    
    total_success = sum(r.get("success", 0) for r in results)
    total_procesados = sum(r.get("total_procesados", 0) for r in results)
    total_skipped = sum(r.get("skipped", 0) for r in results)
    total_api_saved = sum(r.get("api_calls_saved", 0) for r in results)
    
    for result in results:
        db_name = result["db_name"]
        if "error" in result:
            print(f"❌ {db_name}: ERROR - {result['error']}")
        else:
            print(f"✅ {db_name}: {result['success']} asignados, {result.get('api_calls_saved', 0)} API ahorradas")
    
    print(f"\n📊 TOTALES:")
    print(f"   Total procesados: {total_procesados}")
    print(f"   Total asignados: {total_success}")
    print(f"   Total omitidos: {total_skipped}")
    print(f"   💰 TOTAL llamadas API ahorradas: {total_api_saved}")
    
    BotController.log(
        f"🏁 Procesamiento completado: {total_success} asignaciones, {total_api_saved} API ahorradas en {len(DB_NAMES)} BDs",
        "INFO"
    )
    
    print("-" * 35)


if __name__ == "__main__":
    process_pending_lawsuits()