import json
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DATA_FILE = Path('reservas.json')

if not DATA_FILE.exists():
    DATA_FILE.write_text('[]', encoding='utf-8')

class ReservationHandler(SimpleHTTPRequestHandler):
    def _send_json(self, status, body):
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path != '/api/reservas':
            self.send_error(404, 'Not found')
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            self._send_json(400, {'success': False, 'message': 'JSON inválido'})
            return

        nome = data.get('nome', '').strip()
        tel = data.get('tel', '').strip()
        data_reserva = data.get('data', '').strip()
        hora = data.get('hora', '').strip()
        pessoas = data.get('pessoas', '').strip()

        if not (nome and tel and data_reserva and hora and pessoas):
            self._send_json(400, {'success': False, 'message': 'Preencha todos os campos'})
            return

        try:
            reservas = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        except Exception:
            reservas = []

        reserva = {
            'nome': nome,
            'telefone': tel,
            'data': data_reserva,
            'hora': hora,
            'pessoas': pessoas,
        }
        reservas.append(reserva)
        DATA_FILE.write_text(json.dumps(reservas, ensure_ascii=False, indent=2), encoding='utf-8')

        self._send_json(201, {
            'success': True,
            'message': f'Reserva registada para {nome} no dia {data_reserva} às {hora}.',
        })

    def do_GET(self):
        # API de reservas
        if self.path == '/api/reservas':
            try:
                reservas = json.loads(DATA_FILE.read_text(encoding='utf-8'))
            except Exception:
                reservas = []
            self._send_json(200, {'success': True, 'reservas': reservas})
            return

        # Redirecionar URLs com .html para a versão limpa
        parsed = urlsplit(self.path)
        if parsed.path.endswith('.html'):
            clean_path = parsed.path[:-5]
            if clean_path == '/index':
                clean_path = '/'
            if not clean_path.startswith('/'):
                clean_path = '/' + clean_path.lstrip('/')
            location = urlunsplit((parsed.scheme, parsed.netloc, clean_path, parsed.query, parsed.fragment))
            self.send_response(301)
            self.send_header('Location', location)
            self.end_headers()
            return
        
        # Redirecionar root para index.html
        if self.path == '/':
            self.path = '/index.html'
        
        # URLs limpos: /ementa -> /ementa.html
        # Mas só se NÃO for ficheiro estático (css, js, imagens)
        elif not '.' in self.path.split('/')[-1]:
            # Verifica se existe o ficheiro .html
            html_file = Path('.' + self.path + '.html')
            if html_file.exists():
                self.path = self.path + '.html'
            # Se termina com /, adiciona index.html
            elif self.path.endswith('/'):
                self.path = self.path + 'index.html'
        
        # Servir ficheiros estáticos normalmente
        super().do_GET()

if __name__ == '__main__':
    # Railway usa variável de ambiente PORT
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), ReservationHandler)
    print(f'Serving on port {port}')
    server.serve_forever()
