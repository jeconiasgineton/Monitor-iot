import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// API de produção do piloto. Dados fictícios.
const String baseUrl = 'https://monitor-iot-seven.vercel.app';
const String _chaveToken = 'monitor_token';

class ErroApi implements Exception {
  ErroApi(this.mensagem);
  final String mensagem;

  @override
  String toString() => mensagem;
}

class Api {
  String? _token;

  bool get logado => _token != null;

  Future<void> restaurarSessao() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_chaveToken);
  }

  Future<void> entrar(String email, String senha) async {
    final r = await http.post(
      Uri.parse('$baseUrl/v1/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'senha': senha}),
    );
    final dados = await _tratar(r);
    _token = dados['token'] as String;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_chaveToken, _token!);
  }

  Future<void> sair() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_chaveToken);
  }

  Future<List<Map<String, dynamic>>> dispositivos() async {
    final d = await _get('/v1/dispositivos');
    return _lista(d['dispositivos']);
  }

  Future<List<Map<String, dynamic>>> alertasAbertos(String id) async {
    final d = await _get('/v1/dispositivos/$id/alertas?somente_abertos=true');
    return _lista(d['alertas']);
  }

  Future<List<Map<String, dynamic>>> telemetria(String id, {int limite = 50}) async {
    final d = await _get('/v1/dispositivos/$id/telemetria?limite=$limite');
    return _lista(d['leituras']);
  }

  /// Troca a senha. A API encerra as sessões, então o app também sai.
  Future<void> trocarSenha(String atual, String nova) async {
    final r = await http.post(
      Uri.parse('$baseUrl/v1/auth/senha'),
      headers: {..._cabecalhos(), 'Content-Type': 'application/json'},
      body: jsonEncode({'senha_atual': atual, 'senha_nova': nova}),
    );
    await _tratar(r);
    await sair();
  }

  Future<Map<String, dynamic>> _get(String caminho) async {
    final r = await http.get(Uri.parse('$baseUrl$caminho'), headers: _cabecalhos());
    return _tratar(r);
  }

  Map<String, String> _cabecalhos() => {
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  List<Map<String, dynamic>> _lista(dynamic bruto) {
    return (bruto as List).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> _tratar(http.Response r) async {
    Map<String, dynamic> dados = {};
    try {
      dados = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      dados = {};
    }
    if (r.statusCode >= 200 && r.statusCode < 300) {
      return dados;
    }
    final detalhe = dados['detail'];
    final texto = detalhe is String ? detalhe : 'Erro ${r.statusCode}';
    // Sessão expirada: limpa o login para a tela voltar ao início.
    if (r.statusCode == 401 && texto.startsWith('Sessão')) {
      await sair();
      throw ErroApi('Sessão expirada. Entre de novo.');
    }
    throw ErroApi(texto);
  }
}
