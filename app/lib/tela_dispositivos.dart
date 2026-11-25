import 'package:flutter/material.dart';

import 'api.dart';
import 'tela_detalhe.dart';

class TelaDispositivos extends StatefulWidget {
  const TelaDispositivos({super.key, required this.api, required this.aoSair});

  final Api api;
  final VoidCallback aoSair;

  @override
  State<TelaDispositivos> createState() => _TelaDispositivosState();
}

class _TelaDispositivosState extends State<TelaDispositivos> {
  late Future<List<Map<String, dynamic>>> _futuro;

  @override
  void initState() {
    super.initState();
    _futuro = widget.api.dispositivos();
  }

  void _recarregar() {
    setState(() => _futuro = widget.api.dispositivos());
  }

  Future<void> _sair() async {
    await widget.api.sair();
    widget.aoSair();
  }

  Future<void> _abrirTrocaSenha() async {
    await showDialog<void>(
      context: context,
      builder: (_) => _DialogoTrocaSenha(api: widget.api, aoTrocar: widget.aoSair),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dispositivos'),
        actions: [
          IconButton(onPressed: _recarregar, icon: const Icon(Icons.refresh)),
          PopupMenuButton<String>(
            onSelected: (valor) {
              if (valor == 'senha') _abrirTrocaSenha();
              if (valor == 'sair') _sair();
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'senha', child: Text('Trocar senha')),
              PopupMenuItem(value: 'sair', child: Text('Sair')),
            ],
          ),
        ],
      ),
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _futuro,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(snap.error.toString(), textAlign: TextAlign.center),
            ));
          }
          final lista = snap.data ?? [];
          if (lista.isEmpty) {
            return const Center(child: Text('Nenhum dispositivo disponível para este usuário.'));
          }
          return ListView.builder(
            itemCount: lista.length,
            itemBuilder: (_, i) {
              final d = lista[i];
              final id = d['id'] as String;
              return ListTile(
                leading: const Icon(Icons.water_drop_outlined),
                title: Text(id),
                subtitle: Text('Condomínio: ${d['condominio_id']} · Bomba: ${d['bomba_id']}'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => TelaDetalhe(api: widget.api, dispositivoId: id)),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _DialogoTrocaSenha extends StatefulWidget {
  const _DialogoTrocaSenha({required this.api, required this.aoTrocar});

  final Api api;
  final VoidCallback aoTrocar;

  @override
  State<_DialogoTrocaSenha> createState() => _DialogoTrocaSenhaState();
}

class _DialogoTrocaSenhaState extends State<_DialogoTrocaSenha> {
  final TextEditingController _atual = TextEditingController();
  final TextEditingController _nova = TextEditingController();
  String? _erro;
  bool _enviando = false;

  @override
  void dispose() {
    _atual.dispose();
    _nova.dispose();
    super.dispose();
  }

  Future<void> _trocar() async {
    if (_nova.text.length < 10) {
      setState(() => _erro = 'A nova senha precisa ter pelo menos 10 caracteres.');
      return;
    }
    setState(() {
      _enviando = true;
      _erro = null;
    });
    try {
      await widget.api.trocarSenha(_atual.text, _nova.text);
      if (!mounted) return;
      Navigator.of(context).pop();
      widget.aoTrocar();
    } catch (e) {
      if (mounted) setState(() => _erro = e.toString());
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Trocar senha'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _atual,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Senha atual'),
          ),
          TextField(
            controller: _nova,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Nova senha (mín. 10)'),
          ),
          if (_erro != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_erro!, style: const TextStyle(color: Colors.red)),
            ),
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text('Ao trocar, você precisa entrar de novo.'),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: _enviando ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _enviando ? null : _trocar,
          child: Text(_enviando ? 'Salvando...' : 'Trocar'),
        ),
      ],
    );
  }
}
