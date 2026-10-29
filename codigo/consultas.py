# Ariel - consulta por sensor e intervalo [inicio, fim).
def consultar(db, sensor_id, inicio, fim):
    return list(db.Medicoes.find({
        'sensor_id': sensor_id,
        'timestamp': {'$gte': inicio, '$lt': fim}
    }).sort('timestamp', 1))
