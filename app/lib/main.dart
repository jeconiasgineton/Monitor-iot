import 'package:flutter/material.dart';

import 'api.dart';
import 'tela_dispositivos.dart';
import 'tela_login.dart';

void main() {
  runApp(const AppMonitor());
}

class AppMonitor extends StatelessWidget {
  const AppMonitor({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Monitoramento de bombas',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.blue, useMaterial3: true),
      home: const Raiz(),
    );
  }
}

/// Decide entre login e lista, conforme a sessão salva.
class Raiz extends StatefulWidget {
  const Raiz({super.key});

  @override
  State<Raiz> createState() => _RaizState();
}

class _RaizState extends State<Raiz> {
  final Api _api = Api();
  bool _carregando = true;

  @override
  void initState() {
    super.initState();
    _api.restaurarSessao().then((_) {
      if (mounted) setState(() => _carregando = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_carregando) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!_api.logado) {
      return TelaLogin(api: _api, aoEntrar: () => setState(() {}));
    }
    return TelaDispositivos(api: _api, aoSair: () => setState(() {}));
  }
}
