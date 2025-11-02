# celeryconfig.py

broker_url = 'redis://localhost:6379/0'  # oppure 'amqp://admin:admin@localhost:5672//'
result_backend = 'redis://localhost:6379/1'

# Task settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Europe/Rome'
enable_utc = True

# Concurrency
worker_concurrency = 4  # puoi aumentare in base ai core disponibili

# Retry e visibilità
task_acks_late = True
broker_transport_options = {
    'visibility_timeout': 3600  # 1 ora per completare un task
}

# Monitoring
worker_send_task_events = True
task_send_sent_event = True

broker_url = 'amqp://admin:admin@localhost:5672//'
