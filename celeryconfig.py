broker_url = "redis://redis:6379/0"
result_backend = "redis://redis:6379/1"

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "Europe/Rome"
enable_utc = True

worker_concurrency = 4
task_acks_late = True
broker_transport_options = {"visibility_timeout": 3600}

worker_send_task_events = True
task_send_sent_event = True
