# Vercel serverless giriş noktası.
# Vercel'in @vercel/python çalışma zamanı bu dosyadaki `app` ASGI uygulamasını bulur;
# vercel.json'daki rewrite tüm istekleri buraya yönlendirir.
from app.main import app  # noqa: F401
