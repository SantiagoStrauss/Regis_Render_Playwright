from flask import Flask, request, jsonify, Response
from simit import RegistraduriaScraper, RegistraduriaData
import json

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Handle non-ASCII characters

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    nuip = data.get('nuip')
    headless = data.get('headless', True)  # Cambiado el valor predeterminado a False para depuración

    if not nuip:
        return jsonify({'error': 'NUIP is required'}), 400

    scraper = RegistraduriaScraper(headless=headless)
    scraped_data = scraper.scrape(nuip)

    if not scraped_data:
        return jsonify({'error': 'No data found for the provided NUIP'}), 404

    response_data = scraped_data.__dict__
    json_response = json.dumps(response_data, ensure_ascii=False)
    return Response(json_response, mimetype='application/json'), 200

if __name__ == '__main__':
    app.run(debug=True)