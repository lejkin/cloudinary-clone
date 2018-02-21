import os
import json
from flask import Flask, request, render_template, flash, redirect, url_for, abort, send_file
from flask_uploads import (UploadSet, configure_uploads, IMAGES, UploadNotAllowed)
import boto3
from botocore.exceptions import ClientError
from celery import Celery
from werkzeug.routing import BaseConverter
from ImageProcessor import ImageProcessor


try:
    with open('presets.json') as f:
        PRESETS = json.load(f)
except:
    PRESETS = {}

SYNC_PREFIXES        = ['images_staging', 'profile_images_staging']
S3_BUCKET_LOCAL_DIR  = '/opt/cloudinary/tmp'
AWS_S3_BUCKET        = 'bucket_name'


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = 'Aasdas/3yX R~XH#ED#D!D]LWX/,?RT'
app.url_map.converters['regex'] = RegexConverter
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
)



s3 = boto3.client('s3')


photos = UploadSet('photos', IMAGES)

configure_uploads(app, (photos))

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)

@app.route("/")
def hello():
    return "Hello World!"


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = photos.path(filename)
        flash("Photo saved.")
        return redirect(url_for('serve_original', filename=filename))
    return render_template('upload.html')


@app.route('/uploads/<params>/<path:filename>')
def process(params, filename):
    image_path = photos.path(filename)
    options = parse_options(params)
    p = ImageProcessor(image_path)
    buff = p.process(options)
    return send_file(buff, mimetype='image/jpg')


@app.route('/uploads/<path:filename>')
def serve_original(filename):
    image_path = photos.path(filename)
    buff = open(image_path, 'rb')
    return send_file(buff, mimetype='image/jpg')


@app.route('/<path:filename>')
@app.route('/s3/<path:filename>')
def s3serve_original(filename):
    local_file = os.path.join(S3_BUCKET_LOCAL_DIR, filename)
    if os.path.exists(local_file):
        fileobj = local_file
    else:
        fileobj = BytesIO()
        try:
            s3.download_fileobj(AWS_S3_BUCKET, filename, fileobj)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                abort(404)
        fileobj.seek(0)
    return send_file(fileobj, mimetype='image/jpg')


@app.route('/<regex("[whgcrbp]_[^/]+"):params>/<path:filename>')
@app.route('/s3/<regex("[whgcrbp]_[^/]+"):params>/<path:filename>')
def s3process(params, filename):
    options = parse_options(params)
    preset_filename = None

    if 'p' in options:
        preset = options['p']
        # We have a preset - check if we have options for it
        if preset not in PRESETS:
            # Don't have such preset - abort
            abort(404)

        options = parse_options(PRESETS[preset])
        name, ext = os.path.splitext(filename)

        # Preset filename will be like this: 'image.p_stc.jpg'
        preset_filename = ''.join((name, '.p_', preset, ext))

        try:
            s3.head_object(Bucket=AWS_S3_BUCKET, Key=preset_filename)
            return redirect('https://{0}.s3.amazonaws.com/{1}'.format(AWS_S3_BUCKET, preset_filename))
        except ClientError as e:
            # No preset file
            pass

    local_file = os.path.join(S3_BUCKET_LOCAL_DIR, filename)

    if os.path.exists(local_file):
        fileobj = open(local_file, 'rb')
    else:
        fileobj = BytesIO()
        try:
            s3.download_fileobj(AWS_S3_BUCKET, filename, fileobj)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                abort(404)
        fileobj.seek(0)
    p = ImageProcessor(fileobj)
    buff = p.process(options)
    fileobj.close()

    if preset_filename:
        # Upload preset file to S3
        s3.upload_fileobj(buff, AWS_S3_BUCKET, preset_filename, ExtraArgs=dict(ACL='public-read'))
        return redirect('https://{0}.s3.amazonaws.com/{1}'.format(AWS_S3_BUCKET, preset_filename))

    return send_file(buff, mimetype='image/jpg')


def parse_options(raw_options):
    options = {}
    opts_list = raw_options.split(',')
    for opt in opts_list:
        k, w = opt.split('_', 1)
        if '_' in w:
            opts = w.split('_')
        else:
            opts = w
        options[k] = opts
    return options


### automatic sync files from s3 bucket on local server.

@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        3600,
        sync_s3,
    )
    sync_s3.delay()

def download_dir(prefix):
    paginator = s3.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=AWS_S3_BUCKET, Delimiter='/', Prefix=prefix):
        if result.get('CommonPrefixes') is not None:
            for subdir in result.get('CommonPrefixes'):
                prefix = subdir.get('Prefix')
                for allowed_prefix in SYNC_PREFIXES:
                    if prefix.startswith(allowed_prefix):
                        download_dir(prefix)
                        break

        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                local_file = os.path.join(S3_BUCKET_LOCAL_DIR, file.get('Key'))
                if not os.path.exists(os.path.dirname(local_file)):
                    os.makedirs(os.path.dirname(local_file))
                elif not os.path.exists(local_file) or os.path.getsize(local_file) != file.get('Size'):
                    s3.download_file(AWS_S3_BUCKET, file.get('Key'), local_file)

@celery.task
def sync_s3():
    download_dir('')
