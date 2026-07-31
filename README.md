# Telegram VIP Forward Cleaner Bot

Bot Telegram berbasis `aiogram` untuk owner/admin yang dapat menyalin pesan/media terusan ke grup/channel target tanpa label forward, mengelola channel VIP, upload konten VIP, broadcast, preview, dan pembayaran otomatis Pakasir.

## Fitur

- Owner/admin meneruskan foto, video, voice note, dokumen, teks, atau media lain ke bot; bot mengirim ulang ke target dengan `copy_message` sehingga tanda diteruskan hilang.
- Menu user non-admin: **Beli VIP**, **Preview**, dan **Chat Owner**.
- Paket VIP **Perminggu** dan **Permanent**, lengkap dengan keterangan durasi, keuntungan, dan alasan memilih VIP.
- Invoice Pakasir melalui API QRIS, gambar QRIS yang dikirim langsung ke Telegram, tombol cancel, dan pengecekan pembayaran otomatis berkala.
- Setelah pembayaran sukses, bot membuat invite link VIP sekali pakai dan mengirimkannya ke pembeli.
- Notifikasi pembelian sukses ke channel log/database.
- Panel admin: **Tambahkan VIP**, **Upload Konten**, **Atur Preview**, dan **Broadcast** ke semua user yang pernah `/start`.
- MongoDB menyimpan user, pembelian, dan setting runtime.

## Instalasi

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp contoh.env .env
```

Isi `.env`, terutama `BOT_TOKEN`, `OWNER_IDS`, `MONGO_URI`, `PAKASIR_API_KEY`, `VIP_CHANNEL_ID`, `TARGET_CHAT_ID`, dan `PURCHASE_LOG_CHAT_ID`.

> Jangan commit `.env` karena berisi token dan API key rahasia.

## Menjalankan

```bash
python main.py
```

Pastikan bot menjadi admin di channel/grup target dan channel VIP agar dapat mengirim pesan serta membuat invite link.

## Catatan Pakasir

Konfigurasi endpoint Pakasir disimpan di `PAKASIR_BASE_URL` dengan default `https://app.pakasir.com`. Bot membuat transaksi QRIS lewat API Pakasir lalu mengubah QR string menjadi gambar PNG agar Telegram selalu menampilkan QRIS; jika API QRIS sedang tidak dapat dihubungi, bot mengirim QR untuk halaman pembayaran Pakasir mode `qris_only`.
