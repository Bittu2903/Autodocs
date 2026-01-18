import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Database, GitBranch, FileText, RefreshCw, CheckCircle, Clock, TrendingUp 
} from 'lucide-react';
import './App.css';
import { ForceGraph2D } from 'react-force-graph';

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showAddRepo, setShowAddRepo] = useState(false);
  const [activeTab, setActiveTab] = useState('docs'); // 'docs' | 'graph'
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [nodeSet, setNodeSet] = useState(new Set());

  useEffect(() => {
    loadRepositories();
  }, []);

  const loadRepositories = async () => {
    try {
      const res = await axios.get(`${API_BASE}/repositories`);
      setRepositories(res.data);
    } catch (err) {
      console.error('Error loading repositories:', err);
    }
  };

  const loadDocuments = async (repoId) => {
    try {
      const res = await axios.get(`${API_BASE}/repositories/${repoId}/documents`);
      setDocuments(res.data);
    } catch (err) {
      console.error('Error loading documents:', err);
    }
  };

  const addRepository = async (repoData) => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/repositories`, repoData);
      await loadRepositories();
      setShowAddRepo(false);
    } catch (err) {
      alert('Error adding repository');
    }
    setLoading(false);
  };

  const regenerateDocs = async (repoId) => {
    try {
      await axios.post(`${API_BASE}/repositories/${repoId}/regenerate`);
      alert('Documentation regeneration started!');
    } catch (err) {
      alert('Error regenerating docs');
    }
  };
  
  const deleteRepository = async (repoId) => {
    if (!window.confirm('Delete this repository and all generated docs?')) return;
    try {
      await axios.delete(`${API_BASE}/repositories/${repoId}`);
      await loadRepositories();
      if (selectedRepo?.id === repoId) {
        setSelectedRepo(null);
        setDocuments([]);
      }
    } catch (err) {
      alert('Error deleting repository');
    }
  };

  const selectRepository = (repo) => {
    setSelectedRepo(repo);
    loadDocuments(repo.id);
    loadGraph(repo.id);
    setActiveTab('docs');
  };
  
  const loadGraph = async (repoId) => {
    try {
      const res = await axios.get(`${API_BASE}/repositories/${repoId}/graph`);
      const nodes = res.data.nodes || [];
      const links = res.data.links || [];
      setGraphData({ nodes, links });
      setNodeSet(new Set(nodes.map(n => n.id)));
    } catch (err) {
      console.error('Error loading graph:', err);
    }
  };
  
  const expandNode = async (nodeId) => {
    try {
      const res = await axios.get(`${API_BASE}/graph/nodes/${encodeURIComponent(nodeId)}/neighbors`);
      const newNodes = [];
      const ns = new Set(nodeSet);
      for (const n of res.data.nodes || []) {
        if (!ns.has(n.id)) {
          ns.add(n.id);
          newNodes.push(n);
        }
      }
      setNodeSet(ns);
      setGraphData(prev => ({
        nodes: [...prev.nodes, ...newNodes],
        links: [...prev.links, ...(res.data.links || [])]
      }));
    } catch (err) {
      console.error('Error expanding node:', err);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="brand">
            <Database className="accent" />
            <span>AI Documentation Generator</span>
          </div>
          <button className="btn btn-primary" onClick={() => setShowAddRepo(true)}>
            Add Repository
          </button>
        </div>
      </header>
      <div className="container">
        <div className="sidebar">
          <h2>Repositories</h2>
          <div className="repo-list">
            {repositories.map(repo => (
              <div
                key={repo.id}
                className={`repo-item ${selectedRepo?.id === repo.id ? 'active' : ''}`}
                onClick={() => selectRepository(repo)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <GitBranch size={16} />
                  <span style={{ fontWeight: 600 }}>{repo.name}</span>
                </div>
                {repo.status === 'analyzed' ? (
                  <CheckCircle size={16} style={{ color: '#34d399' }} />
                ) : repo.status === 'pending' ? (
                  <Clock size={16} style={{ color: '#f59e0b' }} />
                ) : null}
              </div>
            ))}
          </div>
        </div>
        <div className="main">
          {selectedRepo ? (
            <>
              <div className="card">
                <div className="card-header">
                  <h2 style={{ fontSize: 18, fontWeight: 800 }}>{selectedRepo.name}</h2>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-green" onClick={() => regenerateDocs(selectedRepo.id)}>
                      <RefreshCw size={16} />
                      <span style={{ marginLeft: 8 }}>Regenerate</span>
                    </button>
                    <button className="btn btn-gray" onClick={() => deleteRepository(selectedRepo.id)}>
                      Delete
                    </button>
                  </div>
                </div>
                <div className="stats">
                  <div className="stat blue">
                    <div className="value">{documents.length}</div>
                    <div className="grey">Documents</div>
                  </div>
                  <div className="stat green">
                    <div className="value">{selectedRepo.status === 'analyzed' ? '100%' : '...'}</div>
                    <div className="grey">Complete</div>
                  </div>
                  <div className="stat purple">
                    <div className="value">{selectedRepo.language || 'N/A'}</div>
                    <div className="grey">Language</div>
                  </div>
                </div>
              </div>
              <div className="card">
                <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                  <button
                    className={`btn ${activeTab === 'docs' ? 'btn-primary' : 'btn-gray'}`}
                    onClick={() => setActiveTab('docs')}
                  >
                    Documents
                  </button>
                  <button
                    className={`btn ${activeTab === 'graph' ? 'btn-primary' : 'btn-gray'}`}
                    onClick={() => setActiveTab('graph')}
                  >
                    Graph
                  </button>
                </div>
                {activeTab === 'docs' ? (
                  <div className="docs">
                    {documents.map(doc => (
                      <DocumentCard key={doc.id} doc={doc} />
                    ))}
                  </div>
                ) : (
                  <div style={{ height: 520 }}>
                    <ForceGraph2D
                      graphData={graphData}
                      nodeLabel={n => `${n.type}: ${n.label}`}
                      nodeAutoColorBy="type"
                      linkColor={() => 'rgba(255,255,255,0.3)'}
                      linkDirectionalArrowLength={3.5}
                      linkDirectionalParticles={0}
                      onNodeClick={n => expandNode(n.id)}
                    />
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="card empty">
              <div className="icon">
                <Database size={56} />
              </div>
              <div className="grey">Select a repository to view documentation</div>
            </div>
          )}
        </div>
      </div>
      {showAddRepo && (
        <AddRepositoryModal
          onClose={() => setShowAddRepo(false)}
          onAdd={addRepository}
          loading={loading}
        />
      )}
    </div>
  );
}

function DocumentCard({ doc }) {
  const [expanded, setExpanded] = useState(false);

  const docTypeIcons = {
    architecture: <Database size={20} />,
    api: <GitBranch size={20} />,
    changelog: <TrendingUp size={20} />,
    onboarding: <FileText size={20} />
  };

  return (
    <div className="doc-card">
      <div className="doc-head" onClick={() => setExpanded(!expanded)}>
        <div className="doc-info">
          <div style={{ padding: 8, borderRadius: 10, background: 'rgba(74,179,255,0.2)', border: '1px solid rgba(74,179,255,0.4)' }}>
            {docTypeIcons[doc.doc_type] || <FileText size={20} />}
          </div>
          <div>
            <div style={{ fontWeight: 700 }}>{doc.title}</div>
            <div className="grey">
              {doc.doc_type} • Updated {new Date(doc.updated_at).toLocaleDateString()}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {doc.auto_generated && <span className="badge">AI Generated</span>}
          <span className="badge gray">{doc.confidence_score}% confidence</span>
        </div>
      </div>
      {expanded && (
        <div className="doc-content">
          <pre>{doc.content}</pre>
        </div>
      )}
    </div>
  );
}

function AddRepositoryModal({ onClose, onAdd, loading }) {
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    branch: 'main'
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onAdd(formData);
  };

  return (
    <div className="modal">
      <div className="modal-content">
        <h2 className="modal-title">Add Repository</h2>
        <form onSubmit={handleSubmit} className="form">
          <div>
            <label>Repository Name</label>
            <input
              type="text"
              className="input"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>
          <div>
            <label>Git URL</label>
            <input
              type="text"
              className="input"
              placeholder="https://github.com/user/repo.git"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
            />
          </div>
          <div>
            <label>Branch</label>
            <input
              type="text"
              className="input"
              value={formData.branch}
              onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
            />
          </div>
          <div className="row">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Adding...' : 'Add Repository'}
            </button>
            <button type="button" className="btn btn-gray" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default App;
