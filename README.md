# LocalKart – Multi-vendor marketplace starter

## Run on Windows
1. Extract this ZIP.
2. Open the extracted folder in VS Code.
3. In the terminal run:
   `py -m venv venv`
   `venv\Scripts\activate`
   `pip install -r requirements.txt`
   `python app.py`
4. Open http://127.0.0.1:5000

## Demo admin
Email: admin@localkart.in
Password: Admin@123

Register a customer or vendor account from the website.

## Included in this MVP
- Marketplace homepage, search and category filters
- Customer/vendor registration and login
- Password hashing and role-protected dashboards
- Vendor product listing
- Cart, checkout and Cash on Delivery order creation
- Customer order history
- Admin overview

## Before public deployment
This is a development MVP, not a production-ready commerce platform. Change SECRET_KEY, add CSRF protection, email verification/password reset, secure image uploads, payment gateway integration (Razorpay), shipping/tax logic, order status controls, vendor approval, input validation, rate limiting, backups, HTTPS, and production database configuration. Demo products use remote Unsplash image URLs.
