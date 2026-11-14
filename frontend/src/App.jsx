import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, askQuestion, getHealth } from './api'

const SUGGESTIONS = [
  {
    topic: 'Eligibility',
    question: 'What is the minimum CGPA required for placements?'
  },
  {
    topic: 'Attendance',
    question: 'What are the attendance requirements?'
  },
  {
    topic: 'Applications',
    question: 'Can students apply for multiple companies?'
  },
  {
    topic: 'Offers',
    question: 'What happens if a student rejects an offer?'
  }
]

function createId() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`
}

function Icon({ children, className = '', size = 18 }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
    >
      {children}
    </svg>
  )
}

function SendIcon() {
  return (
    <Icon size={19}>
      <path d="M21 3 10 14" />
      <path d="m21 3-7 18-4-7-7-4 18-7Z" />
    </Icon>
  )
}

function ArrowUpRightIcon() {
  return (
    <Icon size={16}>
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </Icon>
  )
}

function DocumentIcon({ size = 16, className }) {
  return (
    <Icon size={size} className={className}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
      <path d="M8 13h8" />
      <path d="M8 17h5" />
    </Icon>
  )
}

function BookIcon() {
  return (
    <Icon size={16}>
      <path d="M2 4h6a4 4 0 0 1 4 4v12a3 3 0 0 0-3-3H2Z" />
      <path d="M22 4h-6a4 4 0 0 0-4 4v12a3 3 0 0 1 3-3h7Z" />
    </Icon>
  )
}

function ShieldIcon({ size = 15 }) {
  return (
    <Icon size={size}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </Icon>
  )
}

function CheckIcon() {
  return (
    <Icon size={15}>
      <path d="m20 6-11 11-5-5" />
    </Icon>
  )
}

function RefreshIcon() {
  return (
    <Icon size={14}>
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
    </Icon>
  )
}

function InlineText({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={index}>{part.slice(2, -2)}</strong>
    }
    return <Fragment key={index}>{part}</Fragment>
  })
}

function FormattedAnswer({ text }) {
  const lines = text.split(/\r?\n/)
  const blocks = []
  let currentList = null

  const closeList = () => {
    currentList = null
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      closeList()
      continue
    }

    const bullet = line.match(/^[*•-]\s+(.*)$/)
    if (bullet) {
      if (!currentList || currentList.type !== 'ul') {
        currentList = { type: 'ul', items: [] }
        blocks.push(currentList)
      }
      currentList.items.push(bullet[1])
      continue
    }

    const numbered = line.match(/^\d+[.)]\s+(.*)$/)
    if (numbered) {
      if (!currentList || currentList.type !== 'ol') {
        currentList = { type: 'ol', items: [] }
        blocks.push(currentList)
      }
      currentList.items.push(numbered[1])
      continue
    }

    closeList()
    const heading = line.match(/^#{1,6}\s+(.*)$/)
    blocks.push({ type: 'p', text: heading ? heading[1] : line })
  }

  return (
    <div className="answer-text">
      {blocks.map((block, index) => {
        if (block.type === 'ul') {
          return (
            <ul key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <InlineText text={item} />
                </li>
              ))}
            </ul>
          )
        }

        if (block.type === 'ol') {
          return (
            <ol key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <InlineText text={item} />
                </li>
              ))}
            </ol>
          )
        }

        return (
          <p key={index}>
            <InlineText text={block.text} />
          </p>
        )
      })}
    </div>
  )
}

function Sources({ sources }) {
  if (!sources.length) return null

  return (
    <div className="source-block">
      <div className="source-heading">
        <BookIcon />
        <span>Sources</span>
      </div>
      <div className="source-list">
        {sources.map((source, index) => (
          <span
            className="source-chip"
            key={`${source.document}-${source.page ?? 'na'}-${index}`}
            title={`${source.document}${source.page ? `, page ${source.page}` : ''}`}
          >
            <DocumentIcon className="source-icon" size={14} />
            <span className="source-name">{source.document}</span>
            {source.page != null && <span className="source-page">p. {source.page}</span>}
          </span>
        ))}
      </div>
    </div>
  )
}

function App() {
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [connection, setConnection] = useState({
    state: 'checking',
    label: 'Checking backend',
    detail: 'Verifying the API and policy index.',
    documents: null
  })

  const chatBodyRef = useRef(null)
  const textareaRef = useRef(null)
  const inFlightRef = useRef(false)
  const initialHealthCheck = useRef(false)
  const nearBottomRef = useRef(true)

  const refreshHealth = useCallback(async () => {
    setConnection((current) => ({
      ...current,
      state: 'checking',
      label: 'Checking backend',
      detail: 'Verifying the API and policy index.'
    }))

    try {
      const data = await getHealth()
      if (data.status === 'ok') {
        setConnection({
          state: 'online',
          label: 'Backend connected',
          detail: data.message || 'The policy index is ready.',
          documents: data.vector_db?.documents ?? null
        })
      } else if (data.backend?.status === 'connected') {
        setConnection({
          state: 'degraded',
          label: 'Index unavailable',
          detail: data.message || 'The policy index is not ready.',
          documents: data.vector_db?.documents ?? null
        })
      } else {
        setConnection({
          state: 'degraded',
          label: 'Backend degraded',
          detail: data.message || 'The backend reported a problem.',
          documents: null
        })
      }
    } catch (healthError) {
      setConnection({
        state: 'offline',
        label: 'Backend offline',
        detail: healthError.message || 'Could not reach the backend.',
        documents: null
      })
    }
  }, [])

  useEffect(() => {
    if (initialHealthCheck.current) return
    initialHealthCheck.current = true
    refreshHealth()
  }, [refreshHealth])

  const scrollToLatest = useCallback((smooth = true) => {
    const element = chatBodyRef.current
    if (!element) return
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    element.scrollTo({
      top: element.scrollHeight,
      behavior: reduceMotion ? 'auto' : smooth ? 'smooth' : 'auto'
    })
  }, [])

  useEffect(() => {
    const frame = requestAnimationFrame(() => scrollToLatest(true))
    return () => cancelAnimationFrame(frame)
  }, [messages, loading, error, scrollToLatest])

  // Keep the composer and latest message visible when the viewport changes,
  // but do not pull a student away from older messages they are reading.
  useEffect(() => {
    const element = chatBodyRef.current
    if (!element || typeof ResizeObserver === 'undefined') return

    const observer = new ResizeObserver(() => {
      if (nearBottomRef.current) scrollToLatest(false)
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [scrollToLatest])

  const handleChatScroll = useCallback(() => {
    const element = chatBodyRef.current
    if (!element) return
    nearBottomRef.current =
      element.scrollHeight - element.clientHeight - element.scrollTop < 80
  }, [])

  useEffect(() => {
    const element = textareaRef.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, 132)}px`
  }, [question])

  const sendQuestion = useCallback(
    async (rawText, { appendUser = true } = {}) => {
      const text = String(rawText ?? '').trim()
      if (!text || inFlightRef.current) return

      inFlightRef.current = true
      setError(null)
      if (appendUser) {
        setMessages((current) => [
          ...current,
          { id: createId(), role: 'user', text }
        ])
      }
      setLoading(true)

      try {
        const data = await askQuestion(text)
        const answer = data.answer.trim()
        if (!answer) {
          throw new ApiError('The assistant returned an empty answer.', { kind: 'server' })
        }

        const sources = Array.isArray(data.sources)
          ? data.sources
              .filter((source) => source && typeof source.document === 'string')
              .map((source) => ({
                document: source.document,
                page: Number.isInteger(source.page) ? source.page : null
              }))
          : []

        setMessages((current) => [
          ...current,
          { id: createId(), role: 'assistant', text: answer, sources }
        ])
      } catch (requestError) {
        setError({
          message:
            requestError?.message ||
            'The assistant could not answer that question. Please try again.',
          question: text
        })
        if (requestError?.kind === 'network' || requestError?.kind === 'timeout') {
          refreshHealth()
        }
      } finally {
        inFlightRef.current = false
        setLoading(false)
        if (window.innerWidth >= 900) textareaRef.current?.focus()
      }
    },
    [refreshHealth]
  )

  const handleSubmit = (event) => {
    event.preventDefault()
    const text = question.trim()
    if (!text || inFlightRef.current) return
    setQuestion('')
    sendQuestion(text)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      handleSubmit(event)
    }
  }

  const handleSuggestion = (suggestion) => {
    if (inFlightRef.current) return
    setQuestion('')
    sendQuestion(suggestion)
  }

  const handleRetry = () => {
    if (!error || inFlightRef.current) return
    const failedQuestion = error.question
    setError(null)
    sendQuestion(failedQuestion, { appendUser: false })
  }

  const handleNewChat = () => {
    if (inFlightRef.current) return
    setMessages([])
    setError(null)
    setQuestion('')
    textareaRef.current?.focus()
  }

  const connectionLabel =
    connection.state === 'online'
      ? 'Connected'
      : connection.state === 'checking'
        ? 'Checking'
        : connection.state === 'offline'
          ? 'Offline'
          : 'Index unavailable'

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="#top" aria-label="CampusQuery home">
            <span className="brand-mark">CQ</span>
            <span className="brand-copy">
              <span className="brand-name">CampusQuery</span>
              <span className="brand-tagline">Your College Policy Assistant.</span>
            </span>
          </a>

          <nav className="main-nav" aria-label="Primary navigation">
            <a className="nav-link nav-link--active" href="#assistant">
              Assistant
            </a>
            <a className="nav-link" href="#policy">
              Policy
            </a>
          </nav>

          <button
            className={`connection connection--${connection.state}`}
            onClick={refreshHealth}
            title={connection.detail}
            type="button"
            aria-label={`${connectionLabel}. ${connection.detail} Click to check again.`}
          >
            <span className="connection-dot" />
            <span>{connectionLabel}</span>
            <RefreshIcon />
          </button>
        </div>
      </header>

      <main className="page" id="top">
        <section className="hero" aria-labelledby="welcome-heading">
          <div className="hero-copy">
            <span className="eyebrow">
              <span className="eyebrow-line" />
              Official placement policy · 2026–27
            </span>
            <h1 id="welcome-heading">
              Hello! How can I <em>help you?</em>
            </h1>
            <p>
              Ask anything about the official campus placement policy. CampusQuery
              reads the document for you and answers with references to the exact
              pages, so you can check the source yourself.
            </p>
            <div className="hero-meta">
              <span>
                <CheckIcon />
                Policy-grounded answers
              </span>
              <span>
                <BookIcon />
                Page-level references
              </span>
            </div>
          </div>

          <div className="hero-emblem" aria-hidden="true">
            <div className="seal">
              <div className="seal-inner">
                <span className="seal-est">EST. 2026</span>
                <span className="seal-mark">CQ</span>
                <span className="seal-label">CAMPUSQUERY</span>
              </div>
            </div>
            <span className="seal-caption">Official Policy Assistant</span>
          </div>
        </section>

        <section className="workspace" aria-label="CampusQuery assistant">
          <div className="chat-card" id="assistant">
            <div className="chat-head">
              <div className="assistant-id">
                <span className="assistant-avatar">CQ</span>
                <div>
                  <h2>CampusQuery Assistant</h2>
                  <p>Placement policy · Academic Year 2026–27</p>
                </div>
              </div>

              <div className="chat-head-actions">
                <span className="policy-badge">
                  <ShieldIcon />
                  Policy grounded
                </span>
                {messages.length > 0 && (
                  <button
                    className="new-chat"
                    disabled={loading}
                    onClick={handleNewChat}
                    type="button"
                  >
                    New chat
                  </button>
                )}
              </div>
            </div>

            <div
              aria-busy={loading}
              aria-label="Conversation"
              className="chat-body"
              onScroll={handleChatScroll}
              ref={chatBodyRef}
              role="log"
            >
              {messages.length === 0 && !error && (
                <div className="empty-state">
                  <span className="empty-mark">CQ</span>
                  <h3>Ask your first question</h3>
                  <p>
                    Placement policies can be dense. Ask in your own words and
                    CampusQuery will find the relevant sections for you.
                  </p>

                  <div className="suggestions">
                    <span className="suggestions-title">Suggested questions</span>
                    <div className="suggestion-grid">
                      {SUGGESTIONS.map((suggestion, index) => (
                        <button
                          className="suggestion"
                          disabled={loading}
                          key={suggestion.question}
                          onClick={() => handleSuggestion(suggestion.question)}
                          type="button"
                        >
                          <span className="suggestion-index">
                            {String(index + 1).padStart(2, '0')}
                          </span>
                          <span className="suggestion-copy">
                            <span className="suggestion-topic">{suggestion.topic}</span>
                            <span>{suggestion.question}</span>
                          </span>
                          <ArrowUpRightIcon />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {messages.map((message) => (
                <div className={`message message--${message.role}`} key={message.id}>
                  <span className="message-label">
                    {message.role === 'user' ? 'You' : 'CampusQuery'}
                  </span>
                  <div className="bubble">
                    {message.role === 'assistant' ? (
                      <FormattedAnswer text={message.text} />
                    ) : (
                      <p className="answer-text answer-text--plain">{message.text}</p>
                    )}
                    {message.role === 'assistant' && (
                      <>
                        <Sources sources={message.sources || []} />
                        <p className="answer-note">
                          <ShieldIcon size={14} />
                          <span>
                            Please confirm this from your TPC or TR as well —
                            sometimes the AI can be wrong.
                          </span>
                        </p>
                      </>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="message message--assistant" aria-live="polite">
                  <span className="message-label">CampusQuery</span>
                  <div className="bubble typing-bubble">
                    <span className="typing-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <span>Searching the placement policy…</span>
                  </div>
                </div>
              )}

              {error && (
                <div className="error-card" role="alert">
                  <div>
                    <strong>Couldn&apos;t get an answer</strong>
                    <p>{error.message}</p>
                  </div>
                  <button className="retry-button" onClick={handleRetry} type="button">
                    Try again
                  </button>
                </div>
              )}
            </div>

            <form className="composer" onSubmit={handleSubmit}>
              <div className="composer-box">
                <textarea
                  aria-label="Ask a question about the placement policy"
                  maxLength={1000}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about eligibility, attendance, offers, or applications…"
                  ref={textareaRef}
                  rows={1}
                  value={question}
                />
                <button
                  aria-label={loading ? 'Waiting for an answer' : 'Send question'}
                  className="send-button"
                  disabled={loading || !question.trim()}
                  type="submit"
                >
                  {loading ? <span className="send-spinner" /> : <SendIcon />}
                </button>
              </div>
              <div className="composer-hint">
                <span className="keyboard-hint">
                  <kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a
                  new line
                </span>
                <span className="character-count">{question.length}/1000</span>
              </div>
            </form>
          </div>

          <aside className="side-panel" id="policy" aria-label="Policy information">
            <div className="side-card document-card">
              <span className="side-kicker">Source document</span>
              <div className="document-icon-wrap">
                <DocumentIcon size={21} />
              </div>
              <h3>Final Placement Policy</h3>
              <p className="document-subtitle">Academic Year 2026–27</p>

              <div className="document-file">
                <DocumentIcon size={14} />
                <span>Final_Placement_Policy_2026-27.pdf</span>
              </div>

              <div className="document-stats">
                <div>
                  <strong>{connection.documents ?? '—'}</strong>
                  <span>Indexed chunks</span>
                </div>
                <div>
                  <strong>3</strong>
                  <span>Top matches</span>
                </div>
              </div>

              <div className={`index-state index-state--${connection.state}`}>
                <span />
                {connection.state === 'online'
                  ? 'Index ready'
                  : connection.state === 'checking'
                    ? 'Checking index'
                    : 'Index not ready'}
              </div>
            </div>

            <div className="side-card">
              <span className="side-kicker">How it works</span>
              <ol className="steps">
                <li>
                  <span className="step-number">01</span>
                  <div>
                    <strong>Ask naturally</strong>
                    <p>Use your own words. No policy jargon needed.</p>
                  </div>
                </li>
                <li>
                  <span className="step-number">02</span>
                  <div>
                    <strong>Relevant sections found</strong>
                    <p>The policy index retrieves the closest passages.</p>
                  </div>
                </li>
                <li>
                  <span className="step-number">03</span>
                  <div>
                    <strong>Answer with sources</strong>
                    <p>Read the answer, then verify the page references.</p>
                  </div>
                </li>
              </ol>
            </div>

            <p className="side-note">
              CampusQuery answers only from the indexed policy text. If something is
              not covered, it will say so instead of inventing an answer.
            </p>
          </aside>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-brand">
          <span className="footer-mark">CQ</span>
          <span>CampusQuery · Your College Policy Assistant.</span>
        </div>
        <p>Answers are grounded in the official placement policy.</p>
      </footer>
    </div>
  )
}

export default App
