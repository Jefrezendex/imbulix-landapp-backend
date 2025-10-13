Instruções rápidas para subir no Render.com

1) Crie um repositório no GitHub e suba a pasta `backend/` do pacote.
2) No Render, escolha "New" -> "Web Service".
3) Conecte ao repositório GitHub com a pasta que contém main.py.
4) Configure:
   - Branch: main (ou o branch que você usar)
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
5) (Opcional) Defina variáveis de ambiente se necessário.
6) Deploy. O serviço ficará disponível em: https://imbulix-landapp.onrender.com

Observações:
- O backend retorna a URL original do documento para exibição em iframe (opção escolhida).
- O CSV `resultados.csv` será criado na raiz do serviço e persistirá enquanto o serviço roda no container.
- Para persistência permanente entre deploys, considere usar um banco (SQLite, Postgres) ou storage externo.
