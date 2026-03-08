"use client";

import { useRouter } from 'next/navigation';
import { useMemo, useRef, useState } from 'react';
import { addSource, updateSettings, uploadFile } from '@/lib/api';

const sourceTypes = [
  { id: 'website_url', label: 'Website URL', icon: '🌐', desc: 'Paste your docs URL' },
  { id: 'file_upload', label: 'Upload Files', icon: '📄', desc: 'PDF, DOCX, MD, HTML' },
  { id: 'cloud_storage', label: 'Cloud Storage', icon: '☁️', desc: 'S3 / Blob / GCS' },
  { id: 'wiki_kb', label: 'Wiki / Knowledge Base', icon: '📝', desc: 'Confluence, Notion, SharePoint, GitBook' },
  { id: 'git_repo', label: 'Git Repo', icon: '🔗', desc: 'GitHub / GitLab docs/' },
  { id: 'paste_text', label: 'Paste Text', icon: '✏️', desc: 'Raw MD or text editor' },
];

const syncSchedules = ['manual', 'hourly', 'daily', 'weekly'];

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '');
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selType, setSelType] = useState('');
  const [sourceName, setSourceName] = useState('');
  const [endpointSlug, setEndpointSlug] = useState('my-docs');
  const [syncSchedule, setSyncSchedule] = useState('manual');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Source config fields
  const [url, setUrl] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
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
  const [bucket, setBucket] = useState('');
  const [prefix, setPrefix] = useState('');
  const [cloudProvider, setCloudProvider] = useState('s3');
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

  const handleDrop = (e: React.DragEvent) => { e.preventDefault(); setFiles(prev => [...prev, ...Array.from(e.dataTransfer.files)]); };

  const buildConfig = (): any => {
    switch (selType) {
      case 'website_url':
        return { url, sitemap_url: url.replace(/\/?$/, '/sitemap.xml') };
      case 'paste_text':
        return { text: pasteText, title: sourceName };
      case 'wiki_kb':
        if (wikiPlatform === 'confluence') return { platform: 'confluence', base_url: wikiBaseUrl, space_key: wikiSpaceKey, email: wikiEmail, api_token: wikiToken };
        if (wikiPlatform === 'notion') return { platform: 'notion', api_key: notionKey, root_page_id: notionPageId };
        if (wikiPlatform === 'sharepoint') return { platform: 'sharepoint', site_url: wikiBaseUrl };
        return { platform: 'gitbook', base_url: wikiBaseUrl };
      case 'git_repo':
        return { repo_url: repoUrl, branch: repoBranch, docs_path: repoDocsPath, token: repoToken };
      case 'cloud_storage':
        if (cloudProvider === 's3') {
          return { provider: 's3', bucket, prefix, aws_access_key: awsAccessKey, aws_secret_key: awsSecretKey };
        }
        if (cloudProvider === 'azure_blob') {
          return { provider: 'azure_blob', account_url: azureAccountUrl, container: azureContainer, prefix, connection_string: azureConnectionString };
        }
        return { provider: 'gcs', bucket, prefix, service_account_json: gcsServiceAccountJson };
      default:
        return {};
    }
  };

  const handleFinish = async () => {
    setError('');
    setSubmitting(true);
    try {
      // Update endpoint slug
      if (endpointSlug) {
        await updateSettings({ slug: slugify(endpointSlug) });
      }

      // Handle file uploads specially
      if (selType === 'file_upload') {
        if (fileStats.count > 100) {
          throw new Error('Maximum 100 files allowed.');
        }
        if (fileStats.totalBytes > 500 * 1024 * 1024) {
          throw new Error('Total upload size exceeds 500MB.');
        }
        for (const file of files) {
          const result = await uploadFile(file);
          if (result.key && result.bucket) {
            await addSource({
              source_type: 'file_upload',
              name: sourceName || file.name,
              sync_schedule: syncSchedule,
              config: { bucket: result.bucket, key: result.key },
            });
          }
        }
      } else {
        await addSource({
          source_type: selType,
          name: sourceName || sourceTypes.find((t) => t.id === selType)?.label || 'Source',
          sync_schedule: syncSchedule,
          config: buildConfig(),
        });
      }

      router.push('/dashboard');
    } catch (e: any) {
      setError(e?.message || 'Failed to start indexing');
    } finally {
      setSubmitting(false);
    }
  };

  const renderSourceConfig = () => {
    switch (selType) {
      case 'website_url':
        return <input placeholder="https://docs.example.com" value={url} onChange={e => setUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />;
      case 'file_upload':
        return (
          <div onDrop={handleDrop} onDragOver={e => e.preventDefault()} onClick={() => fileRef.current?.click()} className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 transition">
            <input ref={fileRef} type="file" multiple accept=".pdf,.docx,.pptx,.md,.txt,.html" className="hidden" onChange={e => { if (e.target.files) setFiles(prev => [...prev, ...Array.from(e.target.files!)]); }} />
            <p className="text-gray-500 mb-2">Drag & drop files here, or click to browse</p>
            <p className="text-xs text-gray-400">PDF, DOCX, PPTX, Markdown, HTML, TXT — up to 100 files / 500MB total</p>
            {files.length > 0 && <div className="mt-4 text-left space-y-1">{files.map((f, i) => <div key={i} className="text-sm text-gray-700">📎 {f.name} ({(f.size / 1024).toFixed(0)} KB)</div>)}</div>}
            {files.length > 0 && (
              <p className="text-xs text-gray-500 mt-3">Selected {fileStats.count} files ({(fileStats.totalBytes / (1024 * 1024)).toFixed(1)} MB)</p>
            )}
          </div>
        );
      case 'paste_text':
        return <textarea placeholder="Paste your documentation content (markdown supported)" value={pasteText} onChange={e => setPasteText(e.target.value)} rows={8} className="w-full px-4 py-2 border rounded-lg font-mono text-sm" />;
      case 'wiki_kb':
        return (
          <div className="space-y-3">
            <div className="flex gap-2 flex-wrap">
              {['confluence', 'notion', 'sharepoint', 'gitbook'].map(p => (
                <button key={p} onClick={() => setWikiPlatform(p)} className={`px-4 py-2 rounded-lg text-sm capitalize ${wikiPlatform === p ? 'text-white' : 'bg-gray-200'}`} style={wikiPlatform === p ? { background: 'var(--primary)' } : undefined}>{p}</button>
              ))}
            </div>
            {wikiPlatform === 'confluence' && (<>
              <input placeholder="https://mycompany.atlassian.net/wiki" value={wikiBaseUrl} onChange={e => setWikiBaseUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              <input placeholder="Space key (e.g., ENG)" value={wikiSpaceKey} onChange={e => setWikiSpaceKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              <input placeholder="Atlassian email" value={wikiEmail} onChange={e => setWikiEmail(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              <input type="password" placeholder="Atlassian API token" value={wikiToken} onChange={e => setWikiToken(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            </>)}
            {wikiPlatform === 'notion' && (<>
              <input type="password" placeholder="Notion API key (secret_xxx)" value={notionKey} onChange={e => setNotionKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              <input placeholder="Root page ID (optional)" value={notionPageId} onChange={e => setNotionPageId(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            </>)}
            {wikiPlatform === 'sharepoint' && (<>
              <input placeholder="https://mycompany.sharepoint.com/sites/docs" value={wikiBaseUrl} onChange={e => setWikiBaseUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              <input type="password" placeholder="SharePoint access token" value={wikiToken} onChange={e => setWikiToken(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            </>)}
            {wikiPlatform === 'gitbook' && (<>
              <input placeholder="https://myorg.gitbook.io/myspace" value={wikiBaseUrl} onChange={e => setWikiBaseUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              <input type="password" placeholder="GitBook API token" value={wikiToken} onChange={e => setWikiToken(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            </>)}
          </div>
        );
      case 'git_repo':
        return (
          <div className="space-y-3">
            <input placeholder="https://github.com/org/repo" value={repoUrl} onChange={e => setRepoUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
            <div className="grid grid-cols-2 gap-3">
              <input placeholder="Branch (default: main)" value={repoBranch} onChange={e => setRepoBranch(e.target.value)} className="px-4 py-2 border rounded-lg" />
              <input placeholder="Docs folder (default: docs)" value={repoDocsPath} onChange={e => setRepoDocsPath(e.target.value)} className="px-4 py-2 border rounded-lg" />
            </div>
            <input type="password" placeholder="Access token (optional — for private repos)" value={repoToken} onChange={e => setRepoToken(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
          </div>
        );
      case 'cloud_storage':
        return (
          <div className="space-y-3">
            <div className="flex gap-2">
              {['s3', 'azure_blob', 'gcs'].map(p => (
                <button key={p} onClick={() => setCloudProvider(p)} className={`px-4 py-2 rounded-lg text-sm ${cloudProvider === p ? 'text-white' : 'bg-gray-200'}`} style={cloudProvider === p ? { background: 'var(--primary)' } : undefined}>
                  {p === 's3' ? 'AWS S3' : p === 'azure_blob' ? 'Azure Blob' : 'Google Cloud Storage'}
                </button>
              ))}
            </div>
            {cloudProvider === 's3' && (
              <>
                <input placeholder="S3 bucket name" value={bucket} onChange={e => setBucket(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Prefix / folder (optional)" value={prefix} onChange={e => setPrefix(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="AWS access key (optional)" value={awsAccessKey} onChange={e => setAwsAccessKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input type="password" placeholder="AWS secret key (optional)" value={awsSecretKey} onChange={e => setAwsSecretKey(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
            {cloudProvider === 'azure_blob' && (
              <>
                <input placeholder="Azure account URL (optional)" value={azureAccountUrl} onChange={e => setAzureAccountUrl(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Azure container name" value={azureContainer} onChange={e => setAzureContainer(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Prefix / folder (optional)" value={prefix} onChange={e => setPrefix(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <textarea placeholder="Azure Blob connection string" value={azureConnectionString} onChange={e => setAzureConnectionString(e.target.value)} rows={3} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
            {cloudProvider === 'gcs' && (
              <>
                <input placeholder="GCS bucket name" value={bucket} onChange={e => setBucket(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <input placeholder="Prefix / folder (optional)" value={prefix} onChange={e => setPrefix(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
                <textarea placeholder="GCS service account JSON" value={gcsServiceAccountJson} onChange={e => setGcsServiceAccountJson(e.target.value)} rows={4} className="w-full px-4 py-2 border rounded-lg" />
              </>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <main className="min-h-screen page-enter flex items-center justify-center px-4 py-10">
      <div className="card w-full max-w-2xl p-8 mx-4">
        {error && <div className="mb-4 bg-red-100 border border-red-300 text-red-700 rounded px-3 py-2 text-sm">{error}</div>}
        {/* Progress indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3, 4].map(s => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${step >= s ? 'text-white' : 'bg-gray-200 text-gray-500'}`} style={step >= s ? { background: 'var(--primary)' } : undefined}>{s}</div>
              {s < 4 && <div className={`w-12 h-1 rounded ${step > s ? '' : 'bg-gray-200'}`} style={step > s ? { background: 'var(--primary)' } : undefined} />}
            </div>
          ))}
        </div>

        {/* Step 1: Pick source type */}
        {step === 1 && (
          <div>
            <h2 className="text-2xl font-bold mb-2 text-center">How do you want to add your content?</h2>
            <p className="text-gray-500 text-center mb-8">Choose your primary documentation source. You can add more later.</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {sourceTypes.map(t => (
                <button key={t.id} onClick={() => { setSelType(t.id); setStep(2); }} className={`card p-6 transition text-center ${selType === t.id ? '' : ''}`} style={selType === t.id ? { borderColor: 'var(--primary)', background: '#ecf8f6' } : {}}>
                  <div className="text-4xl mb-2">{t.icon}</div>
                  <div className="font-medium">{t.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Source-specific config */}
        {step === 2 && (
          <div>
            <h2 className="text-2xl font-bold mb-2">Configure your source</h2>
            <p className="text-gray-500 mb-6">Provide details for your {sourceTypes.find(t => t.id === selType)?.label} source.</p>
            <div className="space-y-4">
              <input placeholder="Source name (e.g., 'Stripe API Docs')" value={sourceName} onChange={e => setSourceName(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
              {renderSourceConfig()}
              <div className="flex gap-4 mt-6">
                <button onClick={() => setStep(3)} className="btn-primary flex-1">Continue</button>
                <button onClick={() => { setSelType(''); setStep(1); }} className="btn-secondary flex-1">Back</button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Choose endpoint name */}
        {step === 3 && (
          <div>
            <h2 className="text-2xl font-bold mb-2">Name your endpoint</h2>
            <p className="text-gray-500 mb-6">This will be part of your MCP endpoint URL.</p>
            <div className="flex items-center gap-2 mb-6">
              <span className="text-sm text-gray-500 whitespace-nowrap">https://mcp.knowledgemcp.io/mcp/</span>
              <input placeholder="my-docs" value={endpointSlug} onChange={e => setEndpointSlug(slugify(e.target.value))} className="flex-1 px-4 py-2 border rounded-lg font-mono" />
            </div>
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">Default sync schedule</label>
              <select value={syncSchedule} onChange={e => setSyncSchedule(e.target.value)} className="w-full px-4 py-2 border rounded-lg">
                {syncSchedules.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex gap-4">
              <button onClick={() => setStep(4)} className="btn-primary flex-1">Continue</button>
              <button onClick={() => setStep(2)} className="btn-secondary flex-1">Back</button>
            </div>
          </div>
        )}

        {/* Step 4: Start Indexing */}
        {step === 4 && (
          <div className="text-center">
            <div className="text-6xl mb-4">🚀</div>
            <h2 className="text-2xl font-bold mb-2">Ready to index!</h2>
            <p className="text-gray-500 mb-6">
              We'll crawl and index your <strong>{sourceTypes.find(t => t.id === selType)?.label}</strong> source
              {endpointSlug && <> at <code className="bg-gray-100 px-2 py-1 rounded text-sm">/{slugify(endpointSlug)}</code></>}.
            </p>
            <div className="card p-4 mb-6 text-left text-sm">
              <div><strong>Source:</strong> {sourceName || '(unnamed)'}</div>
              <div><strong>Type:</strong> {sourceTypes.find(t => t.id === selType)?.label}</div>
              <div><strong>Endpoint:</strong> https://mcp.knowledgemcp.io/mcp/{slugify(endpointSlug) || 'your-slug'}</div>
              <div><strong>Schedule:</strong> {syncSchedule}</div>
            </div>
            <div className="flex gap-4">
              <button onClick={handleFinish} disabled={submitting} className="btn-primary flex-1 disabled:opacity-50">{submitting ? 'Starting...' : 'Start Indexing'}</button>
              <button onClick={() => setStep(3)} className="btn-secondary flex-1">Back</button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
