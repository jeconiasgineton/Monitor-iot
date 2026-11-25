import 'package:flutter/material.dart';

import 'api.dart';

class TelaDetalhe extends StatefulWidget {
  const TelaDetalhe({super.key, required this.api, required this.dispositivoId});

  final Api api;
  final String dispositivoId;

  @override
  State<TelaDetalhe> createState() => _TelaDetalheState();
}

class _TelaDetalheState extends State<TelaDetalhe> {
  late Future<_Dados> _futuro;

  @override
  void initState() {
    super.initState();
    _futuro = _carregar();
  }

  Future<_Dados> _carregar() async {
    final alertas = await widget.api.alertasAbertos(widget.dispositivoId);
    final leituras = await widget.api.telemetria(widget.dispositivoId, limite: 50);
    return _Dados(alertas: alertas, leituras: leituras);
  }

  void _atualizar() {
    setState(() => _futuro = _carregar());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.dispositivoId),
        actions: [IconButton(onPressed: _atualizar, icon: const Icon(Icons.refresh))],
      ),
      body: FutureBuilder<_Dados>(
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
          final dados = snap.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('Alertas abertos', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              if (dados.alertas.isEmpty)
                const Text('Nenhum alerta aberto.')
              else
                ...dados.alertas.map((a) => Card(
                      color: Colors.red.shade50,
                      child: ListTile(
                        title: Text(a['mensagem'] as String),
                        subtitle: Text('Severidade: ${a['severidade']}'),
                      ),
                    )),
              const SizedBox(height: 16),
              Text('Corrente RMS (últimas leituras)', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              if (dados.leituras.isEmpty)
                const Text('Ainda não há leituras para este dispositivo.')
              else ...[
                SizedBox(
                  height: 200,
                  child: CustomPaint(
                    painter: _GraficoCorrente(_valores(dados.leituras)),
                    size: Size.infinite,
                  ),
                ),
                const SizedBox(height: 8),
                Text(_resumo(dados.leituras)),
              ],
            ],
          );
        },
      ),
    );
  }

  /// Valores em ordem cronológica (a API devolve do mais recente para o mais antigo).
  List<double> _valores(List<Map<String, dynamic>> leituras) {
    return leituras.reversed
        .map((l) => (l['corrente_rms_a'] as num).toDouble())
        .toList();
  }

  String _resumo(List<Map<String, dynamic>> leituras) {
    final valores = _valores(leituras);
    final ultima = valores.last;
    final maximo = valores.reduce((a, b) => a > b ? a : b);
    return 'Última leitura: ${ultima.toStringAsFixed(2)} A · Máximo no período: ${maximo.toStringAsFixed(2)} A';
  }
}

class _Dados {
  _Dados({required this.alertas, required this.leituras});

  final List<Map<String, dynamic>> alertas;
  final List<Map<String, dynamic>> leituras;
}

class _GraficoCorrente extends CustomPainter {
  _GraficoCorrente(this.valores);

  final List<double> valores;

  @override
  void paint(Canvas canvas, Size size) {
    if (valores.isEmpty) return;
    final maximo = valores.reduce((a, b) => a > b ? a : b);
    final escala = maximo <= 0 ? 1.0 : maximo;
    const margem = 12.0;
    final largura = size.width - 2 * margem;
    final altura = size.height - 2 * margem;

    final caneta = Paint()
      ..color = Colors.blue
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final caminho = Path();
    for (var i = 0; i < valores.length; i++) {
      final x = margem + (valores.length == 1 ? 0 : i * largura / (valores.length - 1));
      final y = margem + altura - (valores[i] / escala) * altura;
      if (i == 0) {
        caminho.moveTo(x, y);
      } else {
        caminho.lineTo(x, y);
      }
    }
    canvas.drawPath(caminho, caneta);
  }

  @override
  bool shouldRepaint(covariant _GraficoCorrente antigo) => antigo.valores != valores;
}
