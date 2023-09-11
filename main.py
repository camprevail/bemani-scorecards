import json, importlib, time
from flask import Flask, render_template_string, request, send_file
from lxml import etree
from io import BytesIO
import logging

logging.basicConfig(level=logging.ERROR, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt='%H:%M:%S')
log = logging.getLogger('main')
log.setLevel(logging.INFO)
logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
logging.getLogger('websockets').setLevel(logging.CRITICAL)

app = Flask(__name__, static_url_path='/static')


with open('games.json') as file:
    games = json.load(file)


@app.route("/scorecard", methods=['POST'])
def main():
    data = request.get_data()
    try:
        call = etree.parse(BytesIO(data)).getroot()
        #log.info(etree.tostring(call, pretty_print=True).decode())
    except:
        try:
            call = etree.parse(data).getroot()
            #log.info(etree.tostring(call, pretty_print=True).decode())
        except Exception as e:
            log.info(e)
            return render_template_string('Failed to parse data.'), 500

    try:
        assert call.tag == 'call'  #sanity check
        model, dest, spec, rev, ext = call.get('model').split(':')
    except:
        return render_template_string('invalid data'), 400

    # Route the data to the module within the datecode range in games.json
    for version in games[model]:
        if int(ext) in range(version['min'], version['max'] + 1):
            module = version['module']
            try:
                scorecard = importlib.import_module(f'{module}.scorecard').ScoreCard(data)
                img, info = scorecard.generate()
                log.info(f'Generating {module} scorecard')
                return send_file(img, as_attachment=True, attachment_filename=time.strftime(f"{module}-%Y%m%d-%H%M%S.png"))
            except Exception as e:
                log.error(e)
                return render_template_string(repr(e)), 500
    return render_template_string('game or version not supported'), 406


if __name__ == "__main__":
    app.run(host='0.0.0.0')
