import { useEffect, useRef, useState } from 'react';
import { listKBFiles, uploadKBFile, deleteKBFile } from '../api';

export default function KBPanel() {
  const [files, setFiles] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadFiles = async () => {
    try { setFiles(await listKBFiles()); } catch { /* ignore */ }
  };

  useEffect(() => { loadFiles(); }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setMsg(null);
    try {
      const data = await uploadKBFile(file);
      setMsg({ text: `${data.filename} 已导入 ${data.chunks} 个片段`, ok: true });
      await loadFiles();
    } catch {
      setMsg({ text: '上传失败，请重试', ok: false });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleDelete = async (filename: string) => {
    setDeletingFile(filename);
    try { await deleteKBFile(filename); await loadFiles(); }
    finally { setDeletingFile(null); }
  };

  const getFileIcon = (name: string) => name.endsWith('.md') ? '📝' : name.endsWith('.txt') ? '📄' : '📎';

  return (
    <div className="kb-panel">
      <div className="kb-panel__header">
        <span>知识库文档</span>
        <span className="kb-panel__count">{files.length}</span>
      </div>

      <div
        className={`kb-panel__dropzone${dragOver ? ' kb-panel__dropzone--over' : ''}${uploading ? ' kb-panel__dropzone--uploading' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files?.[0]; if (f) handleUpload(f); }}
        onClick={() => !uploading && inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".md,.txt" style={{ display: 'none' }}
          onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(f); }} disabled={uploading} />
        {uploading ? (
          <div className="kb-panel__dropzone-text"><div className="kb-panel__dropzone-icon">⏳</div>上传中...</div>
        ) : (
          <div className="kb-panel__dropzone-text">
            <div className="kb-panel__dropzone-icon">☁️</div>
            拖拽或点击上传
            <div className="kb-panel__dropzone-hint">.md / .txt</div>
          </div>
        )}
      </div>

      {msg && (
        <div className={`kb-panel__msg ${msg.ok ? 'kb-panel__msg--ok' : 'kb-panel__msg--err'}`}>
          {msg.ok ? '✓ ' : '✗ '}{msg.text}
        </div>
      )}

      <div className="kb-panel__files">
        {files.length === 0 ? (
          <div className="kb-panel__empty">暂无文档</div>
        ) : (
          files.map(f => (
            <div key={f} className="kb-file">
              <span style={{ fontSize: 14, flexShrink: 0 }}>{getFileIcon(f)}</span>
              <span className="kb-file__name">{f}</span>
              <button
                className="kb-file__delete"
                onClick={() => handleDelete(f)}
                disabled={deletingFile === f}
                title="删除"
              >×</button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
