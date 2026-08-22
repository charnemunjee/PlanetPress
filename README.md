\---

# core Django Project

This is a Django web application project that contains the basic eCommerce functionality as well as user authentication for security purposes

\---

## Table of Contents



- [core Django Project](#core-django-project)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Database Setup](#database-setup)
  - [Running the Project](#running-the-project)
  - [Usage](#usage)
  - [Password Reset Testing](#password-reset-testing)
  - [Troubleshooting](#troubleshooting)
  - [Project Structure](#project-structure)
  - [Views](#views)
    - [Base View](#base-view)
    - [Register an account](#register-an-account)
    - [Change password](#change-password)
    - [Sign in](#sign-in)
    - [Roles for users](#roles-for-users)
    - [](#)
      - [Journalist (Independent and linked to a publisher)](#journalist-independent-and-linked-to-a-publisher)

\---

## Prerequisites

Before you begin, ensure you have met the following requirements:

* Python 3.9 or later installed. [Download Python](https://www.python.org/downloads/)
* MySQL installed and running on your machine.
* Basic knowledge of using the command line / terminal.
* Git installed to clone the repository (optional but recommended).

\---

## Installation

1. **Clone the repository** (or download the ZIP and extract):

```bash
   git clone https://github.com/charnemunjee/PlanetPress
   cd PlanetPress
   ```

2. **Create and activate a virtual environment** (recommended):

   * On Windows:

```bash
     python -m venv venv
     venv\\Scripts\\activate
     ```

   * On macOS/Linux:

```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install the required Python packages:**

```bash
   pip install -r requirements.txt
   ```

4. **Configure Email Settings:**

   For sending emails (like password resets), update your email credentials in `PlanetPress/settings.py` under the email section:

   ```python
   EMAIL\_HOST\_USER = 'your-email@example.com'
   EMAIL\_HOST\_PASSWORD = 'your-email-password-or-app-password'
   ```

   > \*\*Note:\*\* For Gmail, you might need to create an App Password and enable "Less secure app access".

   \---

   ## Database Setup

1. **Create MySQL database:**

   Login to your MySQL server and create the database:

   ```sql
   CREATE DATABASE planetpress;
   ```

2. **Update database credentials in `PlanetPress/settings.py`** if your MySQL username or password differ:

   ```python
   DATABASES = {
    'OPTIONS': {
        'init\_command': "SET sql\_mode='STRICT\_TRANS\_TABLES'",
        'charset': 'utf8mb4',
        },
        
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'planetpress',
        'USER': 'ecom\_user',
        'PASSWORD': 'Ler0uxR@$$',
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
      }
   }
   ```



   ## Running the Project

1. **Apply migrations:**

   Run the following commands to create the necessary database tables:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Create a superuser** (for admin access):

   ```bash
   python manage.py createsuperuser
   ```

   Follow the prompts to create a user with admin privileges.

3. **Run the development server:**

   ```bash
   python manage.py runserver
   ```

4. **Access the application:**

   * Open your browser and go to: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   * You can login, register new users, browse products, and test password reset functionality.

   \---

   ## Usage

* **Authentication (`PlanetPress` app):**

  * Click on the link 'Log in!'
  * Login at `/` (root URL)
  * Register at `/register\_user/`
  * Request password reset at `/forgot\_password/`
  * Reset password via emailed token link
* **News Website (`PlanetPress app):**

  * View all products at `/` (root URL, depending on project URL setup)
  * View product details, change prices (if authorized), add to cart, and view cart.

  \---

  ## Password Reset Testing

  If you want to test password reset functionality without sending real emails:

1. Change email backend in `PlanetPress/settings.py` to console:

   ```python
   EMAIL\_BACKEND = "django.core.mail.backends.console.EmailBackend"
   ```

2. When you submit a password reset request, the reset link will print in your console/terminal.
3. Copy and paste the link into your browser to reset the password.

   \---

   ## Troubleshooting

* **MySQL Client Missing Error:**

  If you get `ModuleNotFoundError: No module named 'mysqlclient'`, install it with:

  ```bash
  pip install mysqlclient
  ```

* **SMTP Authentication Error:**

  Make sure you use correct email and password. For Gmail, you might need to use App Passwords instead of your regular password.

* **Static files not loading:**

  During development, Django serves static files automatically. For production, you need to configure static files properly.

  \---

  ## Project Structure

  ```
PlanetPress\_Press/
├── media/
├── PlanetPress/
│   ├── settings.py          # Project settings (DB, email, apps)
│   ├── urls.py              # Root URL routing
│   ├── asgi.py
│   └── wsgi.py
├── posts/              # Authentication app
│   ├── models.py
│   ├── views.py
│   ├── templates/
│   ├── urls.py
│   ├── forms.py
│   ├── apps.py
│   └── admin
├── manage.py                # Django CLI utility
└── requirements.txt         # Python dependencies


## Views
The PlanetPress app will have the following views:

### Base View
The base view allows the user to do the following:
sign in if they have an account
register if they do not have an account
change their password

### Register an account
If the user does not have an account, the user is able to click the "sign up" link
The user can tick the box to indicate whether they would like to join as a buyer or a vendor

### Change password
The user will type in their email address. PlanetPress will check if the email is in the database and will send an email verification link to reset the password

### Sign in
The user can sign in by entering their username and password and clicking on the Log In button


### Roles for users
During the registration process, the user can chose the role they would like to have. These include

* Reader
* Independent Journalist
* Journalist linked to a publisher
* Editor linked to a publisher
* Publisher 

### 

&#x20;  #### Reader permissions
   View articles and newsletters - readers and newsletters can be viewed by the reader. The articles and newsletters that the readers can see

&#x20;  will be based on their preferences at registration stage or if they updated their preferences

&#x20;  Update preferences - readers can update their reading preferences at any time

&#x20;  View the dashboard - each reader has a dashboard that they can view

   #### Journalist (Independent and linked to a publisher)
   Journalists can create, delete and edit articles
   Journalists can create, delete and edit newsletters
   Add an item to their carts by clicking the "Add to cart" button
   change the quantity of an item in their carts
   Proceed to checkout to purchase the item

&#x20;  Note that to sign up as a journalist associated with the publisher, the publisher should also have a user account



&#x20;  #### Editors

&#x20;  Editors can view, delete and edit newsletters and articles
   Review and approve articles for publishing

&#x20;  Note that to sign up as an Editor associated with the publisher, the publisher should also have a user account


&#x20;  #### Publisher

&#x20;  Can have many Journalists and Editors

&#x20;  

\---

