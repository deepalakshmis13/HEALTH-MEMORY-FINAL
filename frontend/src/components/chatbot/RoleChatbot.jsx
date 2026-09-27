import { useEffect, useRef, useState } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import QuickActions from './QuickActions';
import { Badge } from '../common/StatusBadge';
import { useToast } from '../common/Toast';
import chatbotService from '../../services/chatbotService';
import { LOADING_MESSAGES } from '../../utils/constants';
import { useT } from '../../i18n/LanguageContext';

const RETRIEVAL_STEPS = [
  LOADING_MESSAGES.consent,
  LOADING_MESSAGES.retrieval,
  'Composing an evidence-backed answer…',
];

/**
 * One component, four different agents. The role decides the endpoint, the
 * system prompt (server-side), the register of the answer and the quick
 * actions — there is deliberately no single generic chatbot.
 */
export function RoleChatbot({ agent, patientId, patientName, shiftId, height }) {
  const t = useT();
  const toast = useToast();
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [provider, setProvider] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: t(agent.intro),
        sources: [],
      },
    ]);
  }, [agent, patientId]);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, busy]);

  const ask = async (question) => {
    if (!patientId) {
      toast.warning(t('Select a patient before asking a question.'));
      return;
    }
    const history = [...messages, { role: 'user', content: question }];
    setMessages(history);
    setBusy(true);
    setStepIndex(0);
    const ticker = window.setInterval(
      () => setStepIndex((index) => Math.min(index + 1, RETRIEVAL_STEPS.length - 1)),
      600,
    );

    try {
      const response = await chatbotService.ask(agent.role, {
        patientId,
        message: question,
        history: messages.filter((item) => item.role !== 'system'),
        shiftId,
      });
      setProvider(response.provider);
      setMessages([
        ...history,
        {
          role: 'assistant',
          content: response.answer,
          sources: response.sources || [],
          explanation: response.explanation,
          retrieval: response.retrieval,
        },
      ]);
    } catch (error) {
      setMessages([
        ...history,
        {
          role: 'assistant',
          content:
            error.status === 403
              ? error.message
              : `${error.message}\n\n${t(
                  'Nothing has been assumed or invented — the question was not answered.',
                )}`,
          sources: [],
        },
      ]);
      toast.error(error.message, t('AI service could not answer'));
    } finally {
      window.clearInterval(ticker);
      setBusy(false);
    }
  };

  return (
    <div className="chat-panel" style={height ? { height } : undefined}>
      <div className="chat-header">
        <span className="agent-avatar" aria-hidden="true">
          {agent.icon}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="strong">{t(agent.name)}</div>
          <div className="tiny muted">
            {patientName
              ? t('Health memory of {name}', { name: patientName })
              : t('No patient selected')}
            {provider ? ` · ${provider}` : ''}
          </div>
        </div>
        <Badge tone="outline">{t('Consent-filtered')}</Badge>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} agentIcon={agent.icon} />
        ))}
        {busy && (
          <div className="chat-msg">
            <span className="msg-avatar" aria-hidden="true">
              {agent.icon}
            </span>
            <div className="chat-bubble row tight muted">
              <span className="spinner sm" aria-hidden="true" />
              {t(RETRIEVAL_STEPS[stepIndex])}
            </div>
          </div>
        )}
      </div>

      <QuickActions actions={agent.quickActions} onPick={ask} disabled={busy} />
      <ChatInput onSend={ask} busy={busy} />
      <div className="tiny faint" style={{ padding: '0 14px 12px' }}>
        {t(agent.disclaimer)}
      </div>
    </div>
  );
}

export default RoleChatbot;
