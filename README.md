# Monitoramento da Qualidade do Ar - Etapas I e II

Trabalho de Bancos de Dados e Novas Tecnologias - Unochapecó.
Professora: Monica Tissiani De Toni Pereira.

## Integrantes

- Ariel Felipe Marques dos Santos: MongoDB, modelagem e consultas.
- Everton Marlon Berlezi: simulador de sensores.
- Gustavo Desordi: agregações e estatísticas.
- Luiz Eduardo Neckel Ghilardi: Redis e integração final.

## Organização

- codigo/: somente programas Python da aplicação e script de testes.
- documentacao/: relatório técnico com diagrama da arquitetura.
- requirements.txt: bibliotecas Python.

## Executar no Linux

Pré-requisitos: Python 3.9 ou superior com pip/venv, MongoDB Community e Redis
instalados. O servidor MongoDB deve ser compatível com o PyMongo instalado.
O projeto usa localhost:27017 e localhost:6379.

Na pasta raiz do projeto:

```sh
sudo systemctl start mongod
sudo systemctl start redis-server
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python codigo/main.py
```

Os comandos systemctl pressupõem serviços instalados com esses nomes.
Em Debian/Ubuntu, se faltar venv/pip: sudo apt install python3-venv python3-pip.
Instale o MongoDB pelo procedimento oficial da sua distribuição; não confunda
MongoDB Server com o pacote Python pymongo.

Resultados esperados na base do trabalho: 6 sensores em 3 cidades; 288 leituras
por sensor (1728 no total); 12 leituras na consulta S001 das 10h às 11h UTC;
144 resumos por sensor; 72 por cidade; 9 Hashes Redis.

```sh
redis-cli HGETALL qualidadear:sensor:S001
redis-cli HGETALL qualidadear:cidade:SC:chapeco
```

## Testes com outros dados - requisito 1.4 da Etapa II

```sh
python codigo/testes.py
```

O teste usa leituras fixas de 2030, diferentes da carga de demonstração de 2026.
Dois sensores têm quantidades diferentes de leituras: PM2.5 de 10, 20 e 100.
A média global deve ser 130/3, e não a média das médias dos sensores.
São conferidas as cinco médias, dois máximos, contagens, limites da janela,
consulta temporal, carga repetida e a leitura dos últimos resumos no Redis.
O script cria um banco e chaves exclusivos do teste e remove somente esses
recursos ao terminar. Não apaga a base QualidadeAr nem os Hashes da aplicação.
Uma falha gera AssertionError ou erro de conexão; sucesso imprime APROVADO.
