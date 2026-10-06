#!/bin/sh
# Inicialização do contêiner web do FISCO.IA.
set -e

# Se as chaves não forem fornecidas por variável de ambiente, gera-as uma única
# vez e as guarda no volume /data (nunca na imagem nem no repositório).
if [ -z "$SECRET_KEY" ]; then
    [ -f /data/secret_key ] || python -c "import secrets; print(secrets.token_urlsafe(50))" > /data/secret_key
    SECRET_KEY=$(cat /data/secret_key)
    export SECRET_KEY
fi
if [ -z "$FISCO_ENCRYPTION_KEY" ]; then
    [ -f /data/fernet_key ] || python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > /data/fernet_key
    FISCO_ENCRYPTION_KEY=$(cat /data/fernet_key)
    export FISCO_ENCRYPTION_KEY
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput >/dev/null

if [ "$FISCO_SEED_DEMO" = "True" ]; then
    python manage.py seed_demo
fi

exec "$@"
