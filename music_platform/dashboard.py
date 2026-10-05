import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from accounts.models import User
from music.models import Song, ListenHistory, Genre
from playlists.models import Playlist

def dashboard_callback(request, context):
    # Lấy 30 ngày gần nhất thay vì 7 ngày
    today = timezone.now().date()
    days_count = 30
    dates = [(today - timedelta(days=i)) for i in range(days_count - 1, -1, -1)]
    date_labels = [d.strftime("%d/%m") for d in dates]
    
    # Query số lượng User theo ngày
    users_qs = User.objects.filter(created_at__date__gte=dates[0]).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(count=Count('id'))
    
    # Query số lượng Song theo ngày
    songs_qs = Song.objects.filter(created_at__date__gte=dates[0]).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(count=Count('id'))
    
    user_counts = {item['date']: item['count'] for item in users_qs}
    song_counts = {item['date']: item['count'] for item in songs_qs}
    
    user_data = [user_counts.get(d, 0) for d in dates]
    song_data = [song_counts.get(d, 0) for d in dates]
    
    chart_options = {
        "responsive": True,
        "maintainAspectRatio": False,
        "plugins": {
            "legend": {
                "labels": { "color": "#8B9BB4", "font": { "family": "'Plus Jakarta Sans', sans-serif" } }
            }
        },
        "scales": {
            "x": {
                "ticks": { "color": "#8B9BB4", "font": { "family": "'Plus Jakarta Sans', sans-serif" } },
                "grid": { "color": "rgba(255, 255, 255, 0.05)" }
            },
            "y": {
                "beginAtZero": True,
                "ticks": { "color": "#8B9BB4", "font": { "family": "'Plus Jakarta Sans', sans-serif" }, "stepSize": 1 },
                "grid": { "color": "rgba(255, 255, 255, 0.05)" }
            }
        }
    }

    # Line chart data (Tăng trưởng)
    line_chart_data = json.dumps({
        "labels": date_labels,
        "datasets": [
            {
                "label": "Người dùng mới",
                "data": user_data,
                "backgroundColor": "rgba(140, 225, 178, 0.2)", # Mint green transparent
                "borderColor": "#8CE1B2",
                "borderWidth": 2,
                "pointBackgroundColor": "#121929",
                "fill": True,
                "tension": 0.4
            },
            {
                "label": "Bài hát mới",
                "data": song_data,
                "backgroundColor": "rgba(147, 197, 253, 0.2)", # Blue transparent
                "borderColor": "#93C5FD",
                "borderWidth": 2,
                "pointBackgroundColor": "#121929",
                "fill": True,
                "tension": 0.4
            }
        ],
        "options": chart_options
    })

    # Doughnut chart data (Thể loại nhạc)
    genres_qs = Genre.objects.annotate(song_count=Count('songs')).filter(song_count__gt=0).order_by('-song_count')[:6]
    genre_labels = [g.name for g in genres_qs]
    genre_data = [g.song_count for g in genres_qs]
    
    # Màu sắc cho biểu đồ doughnut
    doughnut_colors = ["#8CE1B2", "#93C5FD", "#C4B5FD", "#F9A8D4", "#FCD34D", "#FCA5A5"]
    
    doughnut_chart_data = json.dumps({
        "labels": genre_labels,
        "datasets": [{
            "label": "Số bài hát",
            "data": genre_data,
            "backgroundColor": doughnut_colors,
            "borderColor": "#202A45",
            "borderWidth": 2,
            "borderRadius": 6,
            "barPercentage": 0.6
        }],
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "labels": { "color": "#8B9BB4", "font": { "family": "'Plus Jakarta Sans', sans-serif" } }
                }
            },
            "scales": {
                "x": {
                    "ticks": { "color": "#8B9BB4", "font": { "family": "'Plus Jakarta Sans', sans-serif" } },
                    "grid": { "display": False }
                },
                "y": {
                    "beginAtZero": True,
                    "ticks": { "color": "#8B9BB4", "stepSize": 1, "font": { "family": "'Plus Jakarta Sans', sans-serif" } },
                    "grid": { "color": "rgba(255, 255, 255, 0.05)" }
                }
            }
        }
    })
    
    # Update context with more KPI data
    context.update({
        "line_chart_data": line_chart_data,
        "doughnut_chart_data": doughnut_chart_data,
        "total_users": User.objects.count(),
        "total_songs": Song.objects.count(),
        "total_playlists": Playlist.objects.count(),
        "total_listens": ListenHistory.objects.count()
    })
    
    return context
