### deploy

```
apt install gunicorn
apt install supervisor

cd /etc/supervisor/conf.d
nano cloudinary-app.conf

[program:processingimages]
directory=/opt/cloudinary-app
command=/opt/cloudinary-app/venv/bin/gunicorn app:app -b 0.0.0.0:1088 --chdir /opt/cloudinary-app -w 4
user=root
logfile=/var/log/cloudinary-app.log
log_stderr=true
```

### this config is for automatic update images form s3 bucket to local

```
nano cloudinary-celery.conf

[program:img_celery]
directory = /opt/images_app
environment = PYTHONPATH=/opt/cloudinary-app
command = /opt/cloudinary-app/venv/bin/celery -A 
user = root
stdout_logfile = /var/log/cloudinary-celery.log
stderr_logfile = /var/log/cloudinary-celery.error.log

```



### celery 
```
celery -A app.celery worker -B
```



### nignx 
```
apt-get install nginx
cp nginx/cloudinary.conf /etc/nginx/conf.d/cloudinary.conf
sudo service nginx reload
sudo service nginx restart
```