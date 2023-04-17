One-click Vultr Proxy Setup Application 
=================================================

This project aims to help those who are not familiar with setting up proxies by providing a one-click Vultr proxy setup capability through a Web application built with Flask and Flask-SocketIO.

Features
--------

*   User login and provide Vultr API key
*   One-click creation and configuration of proxy server
*   Display and manage created proxy server instances
*   Connect to the proxy server instance via SSH
*   Provide connection information and status of the proxy server instance

Installation
------------

Make sure you have Python and pip installed. Then run the following command in the project root directory to install the required dependencies:

bash

```bash
pip install -r requirements.txt
```

Running
-------

To run this Flask application, execute the following command in the project root directory:

bash

```bash
python run.py
```

This will start the Flask application on port 10900 locally. Then access [http://localhost:10900](http://localhost:10900) to view and use the application.

File Structure
--------------

Below is the file structure of this one-click Vultr proxy setup application:

arduino

```arduino
.
├── app
│   ├── __init__.py
│   ├── ali_ddns.py
│   ├── main.py
│   ├── routers.py
│   ├── log_utils.py
│   ├── socket_handlers.py
│   ├── socket_log.py
│   ├── socketio_utils.py
│   ├── ssh_romote_utils.py
│   ├── vultr_utils.py
│   └── templates
│       ├── index.html
│       └── login.html
├── requirements.txt
├── config.yml
├── run.py
```

Contributing
------------

Feel free to submit PRs