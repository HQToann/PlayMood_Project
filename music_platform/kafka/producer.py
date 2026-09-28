from django.conf import settings
from confluent_kafka import Producer
import json

# Định nghĩa hàm gửi dữ liệu
def emit_event(topic, key, payload):

    # Kiểm tra kafka đang bật/tắt
    if not settings.KAFKA_ENABLED:
        print(f"[KAFKA DISABLED] Bỏ qua gửi event: {topic}")
        return

    # Giao dữ liệu cho kho chứa
    producer = Producer({'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS})
    producer.produce(topic, key=str(key), value=json.dumps(payload))
    producer.flush()