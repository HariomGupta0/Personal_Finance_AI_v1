import React, { useState, useEffect, useRef } from 'react';
import {
  Scan,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileText,
  Receipt,
  Layers,
  Zap,
  Tag,
  Calendar,
  CreditCard,
  Hash,
  Activity
} from 'lucide-react';

const STAGES = [
  { id: 'prep', label: 'Preparing document', progress: 15 },
  { id: 'scan', label: 'Scanning document', progress: 35 },
  { id: 'ocr', label: 'Detecting text & bounding boxes', progress: 60 },
  { id: 'extract', label: 'Extracting key financial fields', progress: 85 },
  { id: 'validate', label: 'Validating with AI engine', progress: 95 },
  { id: 'done', label: 'Analysis complete', progress: 100 }
];

export default function DocumentScanner({
  file,
  isProcessing,
  error,
  onComplete,
  onCancel,
  extractedData = null
}) {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isPdf, setIsPdf] = useState(false);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [isFinished, setIsFinished] = useState(false);
  const [activeBoxes, setActiveBoxes] = useState([]);
  const stageTimerRef = useRef(null);

  // 1. Generate Object URL for actual file preview
  useEffect(() => {
    if (!file) return;

    const isPdfFile = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    setIsPdf(isPdfFile);

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  // 2. Realistic Stage Progression synced with real processing
  useEffect(() => {
    if (!isProcessing) {
      if (isFinished) return;
      // If done processing without error
      if (extractedData) {
        setCurrentStageIndex(5); // Analysis complete
        setIsFinished(true);
        const timer = setTimeout(() => {
          if (onComplete) onComplete(extractedData);
        }, 900);
        return () => clearTimeout(timer);
      }
      return;
    }

    // Step through first 4 stages naturally while awaiting backend
    let currentIdx = 0;
    setCurrentStageIndex(0);
    setIsFinished(false);

    const advanceStages = () => {
      stageTimerRef.current = setTimeout(() => {
        currentIdx += 1;
        if (currentIdx <= 4) {
          setCurrentStageIndex(currentIdx);
          advanceStages();
        }
      }, currentIdx === 0 ? 500 : currentIdx === 1 ? 900 : currentIdx === 2 ? 800 : 700);
    };

    advanceStages();

    return () => {
      if (stageTimerRef.current) clearTimeout(stageTimerRef.current);
    };
  }, [isProcessing, extractedData, isFinished, onComplete]);

  // 3. Sequentially trigger OCR Bounding Boxes as scan progresses
  useEffect(() => {
    if (currentStageIndex >= 2) {
      setActiveBoxes(['header', 'date']);
    }
    if (currentStageIndex >= 3) {
      setActiveBoxes(['header', 'date', 'amount', 'units', 'ref']);
    }
    if (currentStageIndex < 2) {
      setActiveBoxes([]);
    }
  }, [currentStageIndex]);

  const currentStage = STAGES[currentStageIndex] || STAGES[0];
  const progressPercent = isFinished ? 100 : currentStage.progress;

  return (
    <div className="doc-scanner-modal-backdrop">
      <div className="doc-scanner-card animate-fade-in">
        {/* Scanner Header Bar */}
        <div className="doc-scanner-header">
          <div className="doc-scanner-title-group">
            <div className={`doc-scanner-icon-badge ${isFinished ? 'success' : error ? 'error' : 'pulse'}`}>
              {isFinished ? (
                <CheckCircle2 size={18} className="text-emerald-400" />
              ) : error ? (
                <AlertCircle size={18} className="text-red-400" />
              ) : (
                <Scan size={18} />
              )}
            </div>
            <div>
              <h4 className="doc-scanner-title">
                {isFinished
                  ? 'Document Analysis Complete'
                  : error
                  ? 'Extraction Interrupted'
                  : 'AI Document Vision Scanner'}
              </h4>
              <p className="doc-scanner-subtitle">
                {file?.name || 'Document'} • {(file?.size ? (file.size / 1024).toFixed(1) : 0)} KB
              </p>
            </div>
          </div>

          <div className="doc-scanner-badge-live">
            <span className={`scanner-live-dot ${isFinished ? 'bg-emerald-400' : error ? 'bg-red-400' : 'bg-cyan-400 animate-ping'}`} />
            <span>{isFinished ? 'VERIFIED' : error ? 'ERROR' : 'LIVE OCR ACTIVE'}</span>
          </div>
        </div>

        {/* Center Document Stage Viewport */}
        <div className={`doc-scanner-viewport ${isFinished ? 'scan-success-glow' : ''}`}>
          {/* Animated 4 Corner HUD Brackets */}
          <div className="scanner-corner corner-tl" />
          <div className="scanner-corner corner-tr" />
          <div className="scanner-corner corner-bl" />
          <div className="scanner-corner corner-br" />

          {/* Glowing Laser Beam (Sweeps vertically) */}
          {!isFinished && !error && (
            <div className="scanner-laser-beam">
              <div className="scanner-laser-line" />
              <div className="scanner-laser-trail" />
            </div>
          )}

          {/* Grid Overlay Texture */}
          <div className="scanner-grid-overlay" />

          {/* Document Content (Image / PDF) */}
          <div className="doc-scanner-preview-wrapper">
            {previewUrl && !isPdf ? (
              <img
                src={previewUrl}
                alt="Document preview"
                className="doc-scanner-image"
              />
            ) : previewUrl && isPdf ? (
              <div className="doc-scanner-pdf-card">
                <FileText size={48} className="doc-scanner-pdf-icon" />
                <span className="doc-scanner-pdf-name">{file?.name}</span>
                <span className="badge badge-info" style={{ marginTop: 8 }}>PDF Statement / Invoice</span>
              </div>
            ) : (
              <div className="doc-scanner-placeholder">
                <Receipt size={40} className="text-gray-500" />
                <span>Loading preview...</span>
              </div>
            )}

            {/* Dynamic OCR Bounding Boxes with Labels */}
            {activeBoxes.includes('header') && (
              <div className="ocr-bounding-box box-merchant animate-fade-in" style={{ top: '12%', left: '8%', width: '60%', height: '14%' }}>
                <span className="ocr-box-label"><Tag size={10} /> Merchant / Payee</span>
              </div>
            )}

            {activeBoxes.includes('date') && (
              <div className="ocr-bounding-box box-date animate-fade-in" style={{ top: '28%', right: '8%', width: '42%', height: '11%' }}>
                <span className="ocr-box-label"><Calendar size={10} /> Date & Ref</span>
              </div>
            )}

            {activeBoxes.includes('units') && (
              <div className="ocr-bounding-box box-units animate-fade-in" style={{ top: '44%', left: '8%', width: '84%', height: '20%' }}>
                <span className="ocr-box-label"><Layers size={10} /> Line Items / Units</span>
              </div>
            )}

            {activeBoxes.includes('amount') && (
              <div className="ocr-bounding-box box-amount animate-fade-in" style={{ bottom: '10%', right: '8%', width: '48%', height: '15%' }}>
                <span className="ocr-box-label"><CreditCard size={10} /> Total Amount (₹)</span>
              </div>
            )}
          </div>

          {/* Success Flash Overlay */}
          {isFinished && (
            <div className="doc-scanner-success-overlay animate-fade-in">
              <div className="scanner-success-ring">
                <CheckCircle2 size={54} color="#10b981" />
              </div>
              <span className="scanner-success-text">Data Extracted Successfully</span>
            </div>
          )}
        </div>

        {/* Live Detected Field Highlights Pill Bar */}
        <div className="doc-scanner-detected-chips">
          <div className={`scanner-chip ${activeBoxes.includes('header') ? 'chip-active' : ''}`}>
            <Tag size={12} />
            <span>Merchant: {activeBoxes.includes('header') ? 'Detected' : 'Searching...'}</span>
          </div>
          <div className={`scanner-chip ${activeBoxes.includes('date') ? 'chip-active' : ''}`}>
            <Calendar size={12} />
            <span>Date: {activeBoxes.includes('date') ? 'Detected' : 'Searching...'}</span>
          </div>
          <div className={`scanner-chip ${activeBoxes.includes('amount') ? 'chip-active' : ''}`}>
            <CreditCard size={12} />
            <span>Amount: {activeBoxes.includes('amount') ? 'Detected' : 'Locating...'}</span>
          </div>
          <div className={`scanner-chip ${activeBoxes.includes('units') ? 'chip-active' : ''}`}>
            <Activity size={12} />
            <span>Items/Status: {activeBoxes.includes('units') ? 'Extracted' : 'Detecting...'}</span>
          </div>
        </div>

        {/* Progression Progress Bar & Status */}
        <div className="doc-scanner-footer">
          <div className="doc-scanner-status-text">
            <div className="flex items-center gap-2">
              {!isFinished && !error && <Sparkles size={14} className="text-cyan-400 animate-spin" />}
              <span className="doc-scanner-stage-label">
                {error ? error : currentStage.label}
              </span>
            </div>
            <span className="doc-scanner-percent">{progressPercent}%</span>
          </div>

          <div className="doc-scanner-progress-track">
            <div
              className={`doc-scanner-progress-fill ${isFinished ? 'bg-success' : error ? 'bg-danger' : ''}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {error && (
            <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="btn-secondary" onClick={onCancel} style={{ fontSize: '0.8rem', padding: '6px 14px' }}>
                Dismiss
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
