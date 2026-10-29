# Gustavo - contagem, medias e maximos por hora.
from datetime import datetime, timedelta, timezone


def resumir(db, inicio, fim, tipo):
    grupo = {
        'ano': {'$year': '$timestamp'},
        'mes': {'$month': '$timestamp'},
        'dia': {'$dayOfMonth': '$timestamp'},
        'hora': {'$hour': '$timestamp'}}
    if tipo == 'sensor':
        grupo['sensor_id'] = '$sensor_id'
    elif tipo == 'cidade':
        grupo['cidade'] = '$sensor.localizacao.cidade'
        grupo['uf'] = '$sensor.localizacao.uf'
    else:
        raise ValueError('Informe sensor ou cidade.')

    campos = ['pm25', 'pm10', 'co2', 'temperatura', 'umidade']
    filtro = {'timestamp': {'$gte': inicio, '$lt': fim}}
    # Todos os campos precisam ser numericos para a medicao entrar na contagem.
    for campo in campos:
        filtro[campo] = {'$type': 'number'}
    estatisticas = {'_id': grupo, 'qt_medicoes': {'$sum': 1}}
    for campo in campos:
        estatisticas[campo + '_media'] = {'$avg': '$' + campo}
    estatisticas['pm25_max'] = {'$max': '$pm25'}
    estatisticas['pm10_max'] = {'$max': '$pm10'}
    projecao = {'_id': 1}
    for campo in estatisticas:
        if campo != '_id':
            projecao[campo] = 1
    pipeline = [
        {'$match': filtro},
        {'$lookup': {'from': 'Sensores', 'localField': 'sensor_id',
                     'foreignField': '_id', 'as': 'sensor'}},
        {'$unwind': '$sensor'},
        {'$group': estatisticas},
        {'$project': projecao}]
    resumos = list(db.Medicoes.aggregate(pipeline))
    for resumo in resumos:
        dados = resumo.pop('_id')
        hora = datetime(dados['ano'], dados['mes'], dados['dia'], dados['hora'],
                        tzinfo=timezone.utc)
        resumo['inicio_periodo'] = hora
        resumo['fim_periodo'] = hora + timedelta(hours=1)
        if tipo == 'sensor':
            resumo['sensor_id'] = dados['sensor_id']
        else:
            resumo['cidade'] = dados['cidade']
            resumo['uf'] = dados['uf']
    return resumos
