'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { addSource, deleteSource, getSources, reindexSource, updateSourceSchedule, uploadFile } from '@/lib/api';

const sourceTypes = [
  { id: 'website_url', label: 'Website URL', icon: '🌐' },
  { id: 'file_upload', label: 'Upload Files', icon: '📄' },
  { id: 'cloud_storage', label: 'Cloud Storage', icon: '☁️' },
  { id: 'wiki_kb', label: 'Wiki / KB', icon: '📝' },
  { id: 'git_repo', label: 'Git Repo', icon: '🔗' },
  { id: 'paste_text', label: 'Paste Text', icon: '✏️' },
];

const typeIcons: Record<string, string> = {
  website_url: '🌐', file_upload: '📄', cloud_storage: '☁️', wiki_kb: '📝', git_repo: '🔗', paste_text: '✏️',
};

const scheduleOptions = ['manual', 'hourly', 'daily', 'weekly'];

export default function SourcesPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [show, setShow] = useState(false);
  const [selType, setSelType] = useState('');
  const [name, setName] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [syncSchedule, setSyncSchedule] = useState('manual');
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const [url, setUrl] = useState('');
  const [pasteText, setPasteText] = useState('');

  const [wikiPlatform, setWikiPlatform] = useState('confluence');
  const [wikiBaseUrl, setWikiBaseUrl] = useState('');
  const [wikiSpaceKey, setWikiSpaceKey] = useState('');
  const [wikiEmail, setWikiEmail] = useState('');
  const [wikiToken, setWikiToken] = useState('');
  const [notionKey, setNotionKey] = useState('');
  const [notionPageId, setNotionPageId] = useState('');

  const [repoUrl, setRepoUrl] = useState('');
  const [repoBranch, setRepoBranch] = useState('main');
  const [repoDocsPath, setRepoDocsPath] = useState('docs');
  const [repoToken, setRepoToken] = useState('');

  const [cloudProvider, setCloudProvider] = useState('s3');
  const [bucket, setBucket] = useState('');
  const [prefix, setPrefix] = useState('');
  const [awsAccessKey, setAwsAccessKey] = useState('');
  const [awsSecretKey, setAwsSecretKey] = useState('');
  const [azureAccountUrl, setAzureAccountUrl] = useState('');
  const [azureContainer, setAzureContainer] = useState('');
  const [azureConnectionString, setAzureConnectionString] = useState('');
  const [gcsServiceAccountJson, setGcsServiceAccountJson] = useState('');

  const fileStats = useMemo(() => {
    const totalBytes = files.reduce((acc, f) => acc + f.size, 0);
    return { count: files.length, totalBytes };
  }, [files]);

  const load = async () => {
    const r = await getSources();
    setSources((r.data as any)?.sources ?? []);
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const timer = setInterval(load, 8000);
    return () => clearInterval(timer);
  }, []);

  const resetFields = () => {
    setName('');
    setUrl('');
    setPasteText('');
    setFiles([]);
    setSyncSchedule('manual');

    setWikiPlatform('confluence');
    setWikiBaseUrl('');
    setWikiSpaceKey('');
    setWikiEmail('');
    setWikiToken('');
    setNotionKey('');
    setNotionPageId('');

    setRepoUrl('');
    setRepoBranch('main');
    setRepoDocsPath('docs');
    setRepoToken('');

    setCloudProvider('s3');
    setBucket('');
    setPrefix('');
    setAwsAccessKey('');
    setAwsSecretKey('');
    setAzureAccountUrl('');
    setAzureContainer('');
    setAzureConnectionString('');
    setGcsServiceAccountJson('');
  };

  const buildConfig = () => {
    if (selType === 'website_url') return { url, sitemap_url: url.replace(/\/?$/, '/sitemap.xml') };
    if (selType === 'paste_text') return { text: pasteText, title: name };
    if (selType === 'wiki_kb') {
      if (wikiPlatform === 'confluence') return { platform: 'confluence', base_url: wikiBaseUrl, space_key: wikiSpaceKey, email: wikiEmail, api_token: wikiToken };
      if (wikiPlatform === 'notion') return { platform: 'notion', api_key: notionKey, root_page_id: notionPageId };
      if (wikiPlatform === 'sharepoint') return { platform: 'sharepoint', site_url: wikiBaseUrl };
      return { platform: 'gitbook', base_url: wikiBaseUrl };
    }
    if (selType === 'git_repo') return { repo_url: repoUrl, branch: repoBranch, docs_path: repoDocsPath, token: repoToken };
    if (selType === 'cloud_storage') {
      if (cloudProvider === 's3') return { provider: 's3', bucket, prefix, aws_access_key: awsAccessKey, aws_secret_key: awsSecretKey };
      if (cloudProvider === 'azure_blob') return { provider: 'azure_blob', account_url: azureAccountUrl, container: azureContainer, prefix, connection_string: azureConnectionString };
      return { provider: 'gcs', bucket, prefix, service_account_json: gcsServiceAccountJson };
    }
    return {};
  };

  const handleAdd = async () => {
    setError('');
    try {
      if (selType === 'file_upload') {
        if (fileStats.count === 0) {
          setError('Add at least one file.');
          return;
        }
        if (fileStats.count > 100) {
          setError('Maximum 100 files allowed.');
          return;
        }
        if (fileStats.totalBytes > 500 * 1024 * 1024) {
          setError('Total upload exceeds 500MB.');
          return;
        }

        setUploading(true);
        for (const file of files) {
          const result = await uploadFile(file);
          if (!result.key || !result.bucket) {
            throw new Error(result.error || `Failed to upload ${file.name}`);
          }
          await addSource({
            source_type: 'file_upload',
            name: name || file.name,
            sync_schedule: syncSchedule,
            config: { bucket: result.bucket, key: result.key },
          });
        }
        setUploading(false);
      } else {
        await addSource({
          source_type: selType,
          name: name || sourceTypes.find((s) => s.id === selType)?.label || 'Source',
          sync_schedule: syncSchedule,
          config: buildConfig(),
        });
      }

      setShow(false);
      setSelType('');
      resetFields();
      await load();
    } catch (e: any) {
      setUploading(false);
      setError(e?.message || 'Failed to add source');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setFiles((prev) => [...prev, ...Array.from(e.dataTransfer.files)]);
  };

  const renderForm = () => {
    switch (selType) {
      case 'website_url':
        return <input placeholder="https://docs.example.com" value={url} onChange={(e) => setUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />;

      case 'file_upload':
        return (
          <div onDrop={handleDrop} onDragOver={(e) => e.preventDefault()} onClick={() => fileRef.current?.click()} className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition">
            <input ref={fileRef} type="file" multiple accept=".pdf,.docx,.pptx,.md,.txt,.html" className="hidden" onChange={(e) => { if (e.target.files) setFiles((prev) => [...prev, ...Array.from(e.target.files as FileList)]); }} />
            <p className="text-gray-500 mb-2">Drag and drop files here, or click to browse</p>
            <p className="text-xs text-gray-400">PDF, DOCX, PPTX, Markdown, HTML, TXT</p>
            <p className="text-xs text-gray-400">Limit: 100 files / 500MB total</p>
            {files.length > 0 && <div className="mt-4 text-left space-y-1">{files.map((f, i) => <div key={i} className="text-sm text-gray-700">{f.name} ({(f.size / 1024).toFixed(0)} KB)</div>)}</div>}
            {files.length > 0 && <p className="text-xs text-gray-500 mt-3">Selected {fileStats.count} files ({(fileStats.totalBytes / (1024 * 1024)).toFixed(1)} MB)</p>}
          </div>
        );

      case 'paste_text':
        return <textarea placeholder="Paste markdown/text" value={pasteText} onChange={(e) => setPasteText(e.target.value)} rows={8} className="w-full px-4 py-2 border rounded-lg font-mono text-sm" />;

      case 'wiki_kb':
        return (
          <div className="space-y-3">
            <div className="flex gap-2 flex-wrap">
              {['confluence', 'notion', 'sharepoint', 'gitbook'].map((p) => (
                <button key={p} onClick={() => setWikiPlatform(p)} className={`px-4 py-2 rounded-lg text-sm capitalize ${wikiPlatform === p ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>{p}</button>
              ))}
            </div>
            {wikiPlatform === 'confluence' && (
              <>
                <input placeholder="https://mycompany.atlassian.net/wiki" value={wikiBaseUrl} onChange={(e) => setWikiBaseUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Space key" value={wikiSpaceKey} onChange={(e) => setWikiSpaceKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Email" value={wikiEmail} onChange={(e) => setWikiEmail(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input type="password" placeholder="API token" value={wikiToken} onChange={(e) => setWikiToken(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
            {wikiPlatform === 'notion' && (
              <>
                <input type="password" placeholder="Notion API key" value={notionKey} onChange={(e) => setNotionKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Root page ID (optional)" value={notionPageId} onChange={(e) => setNotionPageId(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
            {wikiPlatform === 'sharepoint' && (
              <input placeholder="https://mycompany.sharepoint.com/sites/docs" value={wikiBaseUrl} onChange={(e) => setWikiBaseUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            )}
            {wikiPlatform === 'gitbook' && (
              <input placeholder="https://myorg.gitbook.io/myspace" value={wikiBaseUrl} onChange={(e) => setWikiBaseUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            )}
          </div>
        );

      case 'git_repo':
        return (
          <div className="space-y-3">
            <input placeholder="https://github.com/org/repo" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            <div className="grid grid-cols-2 gap-3">
              <input placeholder="Branch" value={repoBranch} onChange={(e) => setRepoBranch(e.target.value)} className="px-4 py-2 border rounded-lg" />
              <input placeholder="Docs folder" value={repoDocsPath} onChange={(e) => setRepoDocsPath(e.target.value)} className="px-4 py-2 border rounded-lg" />
            </div>
            <input type="password" placeholder="Token (optional)" value={repoToken} onChange={(e) => setRepoToken(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
          </div>
        );

      case 'cloud_storage':
        return (
          <div className="space-y-3">
            <div className="flex gap-2">
              {['s3', 'azure_blob', 'gcs'].map((p) => (
                <button key={p} onClick={() => setCloudProvider(p)} className={`px-4 py-2 rounded-lg text-sm ${cloudProvider === p ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>{p}</button>
              ))}
            </div>
            {cloudProvider === 's3' && (
              <>
                <input placeholder="S3 bucket" value={bucket} onChange={(e) => setBucket(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Prefix (optional)" value={prefix} onChange={(e) => setPrefix(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="AWS access key (optional)" value={awsAccessKey} onChange={(e) => setAwsAccessKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input type="password" placeholder="AWS secret key (optional)" value={awsSecretKey} onChange={(e) => setAwsSecretKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
            {cloudProvider === 'azure_blob' && (
              <>
                <input placeholder="Account URL (optional)" value={azureAccountUrl} onChange={(e) => setAzureAccountUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Container name" value={azureContainer} onChange={(e) => setAzureContainer(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Prefix (optional)" value={prefix} onChange={(e) => setPrefix(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <textarea placeholder="Connection string" value={azureConnectionString} onChange={(e) => setAzureConnectionString(e.target.value)} rows={3} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
            {cloudProvider === 'gcs' && (
              <>
                <input placeholder="GCS bucket" value={bucket} onChange={(e) => setBucket(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Prefix (optional)" value={prefix} onChange={(e) => setPrefix(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <textarea placeholder="Service account JSON" value={gcsServiceAccountJson} onChange={(e) => setGcsServiceAccountJson(e.target.value)} rows={4} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <main className="container py-10">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold">Sources</h1>
        <button onClick={() => setShow(true)} className="btn-primary">+ Add Source</button>
      </div>

      {sources.length === 0 && (
        <div className="card p-8 mb-8 border-2 border-dashed border-blue-300 bg-blue-50 text-center">
          <h2 className="text-2xl font-bold mb-3">Welcome! Add your first documentation source.</h2>
          <p className="text-gray-600 mb-6">Paste a URL, upload files, connect wiki/cloud/git, or paste text.</p>
          <button onClick={() => setShow(true)} className="btn-primary">+ Add Your First Source</button>
        </div>
      )}

      {show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="card p-8 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold mb-2">Add Documentation Source</h2>
            <p className="text-sm text-gray-500 mb-6">All sources merge into one search index.</p>
            {error && <div className="mb-4 p-3 border border-red-300 rounded bg-red-50 text-red-700 text-sm">{error}</div>}

            {!selType ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {sourceTypes.map((t) => (
                  <button key={t.id} onClick={() => setSelType(t.id)} className="card p-6 hover:border-blue-600 transition text-center">
                    <div className="text-4xl mb-2">{t.icon}</div>
                    <div className="font-medium">{t.label}</div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                <button onClick={() => { setSelType(''); resetFields(); setError(''); }} className="text-blue-600 hover:underline">← Back</button>
                <input placeholder="Source name" value={name} onChange={(e) => setName(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                {renderForm()}
                <div>
                  <label className="block text-sm font-medium mb-1">Sync schedule</label>
                  <select value={syncSchedule} onChange={(e) => setSyncSchedule(e.target.value)} className="w-full px-4 py-2 border rounded-lg">
                    {scheduleOptions.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="flex gap-4">
                  <button onClick={handleAdd} disabled={uploading} className="btn-primary flex-1 disabled:opacity-50">{uploading ? 'Uploading...' : 'Start Indexing'}</button>
                  <button onClick={() => { setShow(false); setSelType(''); resetFields(); setError(''); }} className="btn-secondary flex-1">Cancel</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {sources.map((s: any) => {
          const status = s.status || 'pending';
          const docs = s.doc_count || s.pages_indexed || 0;
          const isActive = ['pending', 'crawling', 'indexing', 'reindexing'].includes(status);
          const indexed = typeof s.pages_indexed === 'number' ? s.pages_indexed : 0;
          const found = typeof s.pages_found === 'number' ? s.pages_found : 0;
          const hasDeterministicProgress = found > 0;
          const progressPct = hasDeterministicProgress ? Math.max(0, Math.min(100, Math.round((indexed / found) * 100))) : 0;
          return (
            <div key={s.source_id} className="card p-6">
              <div className="flex justify-between items-start gap-4">
                <div className="flex items-start gap-4">
                  <span className="text-3xl">{typeIcons[s.source_type] ?? '📄'}</span>
                  <div>
                    <h3 className="font-bold text-lg">{s.name}</h3>
                    <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${status === 'ready' ? 'bg-green-100 text-green-700' : status === 'failed' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>{status}</span>
                      <span>{docs} docs</span>
                      {s.updated_at && <span>Synced {new Date(s.updated_at).toLocaleString()}</span>}
                      <span className="capitalize">Schedule: {s.sync_schedule || 'manual'}</span>
                    </div>
                    {isActive && (
                      <div className="w-64 mt-3">
                        <div className="h-2 bg-gray-200 rounded overflow-hidden">
                          <div
                            className={`h-2 rounded ${hasDeterministicProgress ? '' : 'animate-pulse'}`}
                            style={{
                              width: hasDeterministicProgress ? `${progressPct}%` : '100%',
                              background: 'linear-gradient(90deg, #9fd4ca 0%, #2e7d74 50%, #9fd4ca 100%)',
                            }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Live status refreshes every 8s
                          {hasDeterministicProgress
                            ? ` · ${indexed}/${found} chunks (${progressPct}%)`
                            : (typeof s.pages_indexed === 'number' ? ` · ${s.pages_indexed} chunks indexed` : '')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-2">
                  <button onClick={async () => { await reindexSource(s.source_id); await load(); }} className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm hover:bg-blue-200">Reindex</button>
                  <select
                    className="px-2 py-1 border rounded text-sm"
                    value={s.sync_schedule || 'manual'}
                    onChange={async (e) => {
                      await updateSourceSchedule(s.source_id, e.target.value);
                      await load();
                    }}
                  >
                    {scheduleOptions.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                  <button onClick={async () => { if (confirm('Delete this source and all indexed content?')) { await deleteSource(s.source_id); await load(); } }} className="px-3 py-1 bg-red-100 text-red-700 rounded text-sm hover:bg-red-200">Delete</button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
