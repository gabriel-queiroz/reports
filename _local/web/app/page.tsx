"use client";

import { useEffect, useRef, useState } from "react";

type Papel = "user" | "agente" | "erro";
type Mensagem = { papel: Papel; texto: string };
type Relatorio = { id: string; groupId: string; userId: string; query: string };
type Saude = { status: string; llm: string; sessoes: number; relatorios: number };

const GROUP_ID_PADRAO = "550e8400-e29b-41d4-a716-446655440000";

const SUGESTOES = [
  "quantos colaboradores ativos por empresa?",
  "recargas de julho por empresa",
  "notas fiscais emitidas este mês",
  "colaboradores desligados em julho",
];

/** Heurística local só para destacar no console — o validador de verdade é o do agente. */
function suspeitas(sql: string): string[] {
  const achados: string[] = [];
  const s = sql.replace(/\s+/g, " ");
  if (/\b(GROUP BY|ORDER BY)\b[^]*\bAND\b[^]*\bLIMIT\b/i.test(s))
    achados.push("filtro aparentemente injetado depois de GROUP BY/ORDER BY — SQL inválido");
  if (!/company_group_id\s+AS\s+company_group_id/i.test(s))
    achados.push("sem coluna de saída `company_group_id`");
  if (!/\b(company_group_id|group_id|company_group\.id)\s*=\s*'/i.test(s))
    achados.push("sem filtro de grupo no WHERE");
  if (/;/.test(s.replace(/;$/, ""))) achados.push("mais de um statement");
  return achados;
}

export default function Console() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [relatorios, setRelatorios] = useState<Relatorio[]>([]);
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [saude, setSaude] = useState<Saude | null>(null);
  const [sessao, setSessao] = useState("");
  const [groupId, setGroupId] = useState(GROUP_ID_PADRAO);
  const [userId, setUserId] = useState("usuario-de-teste");
  const fimChat = useRef<HTMLDivElement>(null);

  useEffect(() => setSessao(crypto.randomUUID()), []);
  useEffect(() => {
    const ler = () =>
      fetch("/agent/health")
        .then((r) => r.json())
        .then(setSaude)
        .catch(() => setSaude(null));
    ler();
    const t = setInterval(ler, 5000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    fimChat.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, ocupado]);

  async function enviar(pergunta: string) {
    const t = pergunta.trim();
    if (!t || ocupado) return;
    setTexto("");
    setMensagens((m) => [...m, { papel: "user", texto: t }]);
    setOcupado(true);
    try {
      const r = await fetch("/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: t,
          session_id: sessao,
          group_id: groupId,
          user_id: userId,
        }),
      });
      const j = await r.json();
      setMensagens((m) => [
        ...m,
        { papel: "agente", texto: j.response ?? "(sem resposta)" },
        ...(j.error_message
          ? [{ papel: "erro" as Papel, texto: `erro: ${j.error_message}` }]
          : []),
      ]);
      const novos: Relatorio[] = j.relatorios_gerados_nesta_chamada ?? [];
      if (novos.length) setRelatorios((r0) => [...novos, ...r0]);
    } catch (e) {
      setMensagens((m) => [
        ...m,
        { papel: "erro", texto: `falha ao chamar a API: ${e}` },
      ]);
    } finally {
      setOcupado(false);
    }
  }

  async function limpar() {
    if (sessao) await fetch(`/agent/sessions/${sessao}`, { method: "DELETE" });
    setSessao(crypto.randomUUID());
    setMensagens([]);
  }

  const pillLlm = !saude ? "off" : saude.llm === "openai" ? "ok" : "fake";

  return (
    <div className="app">
      <header className="topo">
        <h1>Reports B2B · console</h1>
        <span className={`pill ${pillLlm}`}>
          {!saude ? "API offline" : `LLM: ${saude.llm}`}
        </span>
        {sessao && <span className="pill">sessão {sessao.slice(0, 8)}</span>}
        <div className="campos">
          <div className="campo">
            <label htmlFor="gid">group_id</label>
            <input id="gid" value={groupId} onChange={(e) => setGroupId(e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="uid">user_id</label>
            <input
              id="uid"
              className="curto"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
        </div>
      </header>

      <div className="corpo">
        <section className="coluna">
          <div className="cabecalho">
            <span>Conversa</span>
            <button onClick={limpar}>nova sessão</button>
          </div>
          <div className="rolagem">
            {mensagens.length === 0 && (
              <p className="vazio">
                Peça um relatório. O agente confirma o escopo antes de gerar — responda
                &quot;sim&quot; para seguir.
              </p>
            )}
            {mensagens.map((m, i) => (
              <div key={i} className={`msg ${m.papel}`}>
                <div className="autor">
                  {m.papel === "user" ? "você" : m.papel === "erro" ? "erro" : "agente"}
                </div>
                <div className="balao">{m.texto}</div>
              </div>
            ))}
            {ocupado && <div className="pensando">agente pensando…</div>}
            <div ref={fimChat} />
          </div>
          <div className="sugestoes">
            {SUGESTOES.map((s) => (
              <button key={s} onClick={() => enviar(s)} disabled={ocupado}>
                {s}
              </button>
            ))}
          </div>
          <form
            className="entrada"
            onSubmit={(e) => {
              e.preventDefault();
              enviar(texto);
            }}
          >
            <input
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Ex.: quantos colaboradores ativos por empresa?"
              disabled={ocupado}
            />
            <button type="submit" disabled={ocupado || !texto.trim()}>
              Enviar
            </button>
          </form>
        </section>

        <section className="coluna">
          <div className="cabecalho">
            <span>SQL entregue ao Reports Service</span>
            <span>{relatorios.length}</span>
          </div>
          <div className="rolagem">
            {relatorios.length === 0 && (
              <p className="vazio">
                Nada ainda. O SQL aparece aqui quando o agente confirma o relatório e chama a
                tool.
              </p>
            )}
            {relatorios.map((r) => {
              const alertas = suspeitas(r.query);
              return (
                <article key={r.id} className="relatorio">
                  <header>
                    <span>report {r.id.slice(0, 8)}</span>
                    <span>group {r.groupId?.slice(0, 8)}</span>
                  </header>
                  <pre>{r.query}</pre>
                  {alertas.map((a) => (
                    <p key={a} className="alerta">
                      ⚠ {a}
                    </p>
                  ))}
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
