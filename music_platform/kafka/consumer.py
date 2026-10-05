from confluent_kafka import Consumer
from django.conf import settings

# Khai báo hàm giao hàng
def start_consumer():
    # khai báo hàm làm việc
    c = Consumer(
        {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'notification-group',
            'auto.offset.reset': 'earliest',
        },
    )
    # chọn đúng hòm thư cần canh
    c.subscribe(['playmood.song.published'])

    # vòng lặp làm việc liên tục
    while True:
        msg = c.poll(1.0)
        # kiểm tra lại đúng hàng
        if msg is None: continue
        if msg.error(): continue

        # tạo notification trong database ở đây
        print(f"Nhận được bài hát mới: {msg.value().decode('utf-8')}", flush=True)