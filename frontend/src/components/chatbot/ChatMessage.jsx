import EvidencePanel from './EvidencePanel';

export function ChatMessage({ message, agentIcon = '🤖' }) {
  const isUser = message.role === 'user';
  return (
    <div className={`chat-msg${isUser ? ' user' : ''}`}>
      <span className="msg-avatar" aria-hidden="true">
        {isUser ? '🙂' : agentIcon}
      </span>
      <div style={{ minWidth: 0 }}>
        <div className="chat-bubble">{message.content}</div>
        {!isUser && (
          <EvidencePanel
            sources={message.sources}
            explanation={message.explanation}
            retrieval={message.retrieval}
          />
        )}
      </div>
    </div>
  );
}

export default ChatMessage;
