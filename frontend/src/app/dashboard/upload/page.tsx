"use client";

import { useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import {
  ImageIcon,
  Video,
  Mic,
  FileText,
  Link2,
  UploadCloud,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { api, ApiError, ApiPaths, getToken, API_URL } from "@/lib/api";
import { Scan, ScanCreatedResponse, ScanType } from "@/lib/types";
import { cn, formatBytes } from "@/lib/utils";
import ScoreBar from "@/components/ScoreBar";

const TABS: {
  id: ScanType;
  label: string;
  icon: any;
  accept: Record<string, string[]>;
}[] = [
  {
    id: "image",
    label: "Image",
    icon: ImageIcon,
    accept: { "image/*": [".jpg", ".jpeg", ".png"] },
  },
  {
    id: "video",
    label: "Video",
    icon: Video,
    accept: { "video/*": [".mp4", ".mov", ".webm"] },
  },
  {
    id: "audio",
    label: "Audio",
    icon: Mic,
    accept: { "audio/*": [".mp3", ".wav", ".m4a", ".ogg", ".flac"] },
  },
  { id: "text", label: "Text", icon: FileText, accept: {} },
  { id: "url", label: "URL", icon: Link2, accept: {} },
];

export default function UploadPage() {
  const [activeTab, setActiveTab] = useState<ScanType>("image");
  const [submitting, setSubmitting] = useState(false);
  const [scan, setScan] = useState<Scan | null>(null);
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const router = useRouter();

  const { getRootProps, getInputProps, acceptedFiles, isDragActive, open } =
    useDropzone({
      accept: TABS.find((t) => t.id === activeTab)?.accept,
      multiple: false,
      noClick: true,
      noKeyboard: true,
      disabled: submitting || activeTab === "text" || activeTab === "url",
    });

  const file = acceptedFiles[0];

  useEffect(() => {
    if (!scan || ["completed", "failed", "rejected"].includes(scan.status))
      return;
    const interval = setInterval(async () => {
      try {
        const updated = await api<Scan>(ApiPaths.scan(scan.id));
        setScan(updated);
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [scan]);

  async function handleSubmit() {
    setSubmitting(true);
    setScan(null);
    try {
      let created: ScanCreatedResponse;

      if (activeTab === "text") {
        if (!text.trim()) throw new ApiError(400, "Please enter some text.");
        created = await api<ScanCreatedResponse>(ApiPaths.text, {
          body: { text },
        });
      } else if (activeTab === "url") {
        if (!url.trim()) throw new ApiError(400, "Please enter a URL.");
        created = await api<ScanCreatedResponse>(ApiPaths.url, {
          body: { url },
        });
      } else {
        if (!file) throw new ApiError(400, "Please choose a file.");
        const fd = new FormData();
        fd.append("file", file);
        const path = {
          image: ApiPaths.image,
          video: ApiPaths.video,
          audio: ApiPaths.audio,
        }[activeTab];
        created = await api<ScanCreatedResponse>(path!, { formData: fd });
      }

      toast.success("Upload accepted — virus scan & processing started.");
      const initial = await api<Scan>(ApiPaths.scan(created.scan_id));
      setScan(initial);
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : "Upload failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  const isFile =
    activeTab === "image" || activeTab === "video" || activeTab === "audio";

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full">
      <div className="mb-5 sm:mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          New scan
        </h1>
        <p className="text-slate-500 text-sm flex items-center gap-1.5 mt-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          Every upload is virus-scanned with ClamAV before any AI processing.
        </p>
      </div>

      <div className="card p-1.5 mb-5 sm:mb-6 flex flex-wrap gap-1 overflow-x-auto no-scrollbar">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => {
              setActiveTab(id);
              setScan(null);
            }}
            className={cn(
              "relative flex items-center gap-2 rounded-xl px-3 sm:px-4 py-2 text-sm font-medium transition whitespace-nowrap",
              activeTab === id
                ? "text-white"
                : "text-slate-600 hover:bg-slate-100"
            )}
          >
            {activeTab === id && (
              <motion.span
                layoutId="upload-tab"
                className="absolute inset-0 rounded-xl bg-gradient-to-r from-brand-600 to-fuchsia-600 shadow"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative flex items-center gap-2">
              <Icon className="w-4 h-4" />
              {label}
            </span>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <div className="card p-4 sm:p-6">
          <h2 className="font-semibold mb-3 sm:mb-4 capitalize">
            {activeTab} input
          </h2>

          {isFile && (
            <div
              {...getRootProps()}
              className={cn(
                "border-2 border-dashed rounded-2xl p-6 sm:p-10 text-center transition cursor-pointer relative overflow-hidden",
                isDragActive
                  ? "border-brand-500 bg-brand-50 scale-[1.01]"
                  : "border-slate-200 hover:border-brand-400 hover:bg-slate-50/50"
              )}
              onClick={open}
            >
              <input {...getInputProps()} />
              <motion.div
                animate={isDragActive ? { y: [-2, 2, -2] } : { y: 0 }}
                transition={{
                  duration: 1,
                  repeat: isDragActive ? Infinity : 0,
                }}
              >
                <UploadCloud className="w-10 h-10 sm:w-12 sm:h-12 mx-auto text-brand-500 mb-3" />
              </motion.div>
              {file ? (
                <>
                  <div className="font-medium break-all">{file.name}</div>
                  <div className="text-sm text-slate-500 mt-1">
                    {formatBytes(file.size)} · {file.type || "unknown"}
                  </div>
                </>
              ) : (
                <>
                  <div className="font-medium">
                    Drop your file here, or click to browse
                  </div>
                  <div className="text-xs sm:text-sm text-slate-500 mt-1">
                    Allowed:{" "}
                    {Object.values(TABS.find((t) => t.id === activeTab)!.accept)
                      .flat()
                      .join(", ")}
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === "text" && (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={10}
              className="input resize-none"
              placeholder="Paste any text here to check if it was AI-generated…"
            />
          )}

          {activeTab === "url" && (
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              type="url"
              className="input"
              placeholder="https://example.com/article-or-post"
            />
          )}

          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="btn-primary w-full mt-5 sm:mt-6"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Submitting…
              </>
            ) : (
              <>Run detection</>
            )}
          </button>
        </div>

        <div className="card p-4 sm:p-6">
          <h2 className="font-semibold mb-3 sm:mb-4">Result</h2>
          <AnimatePresence mode="wait">
            {!scan && (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-slate-400 text-sm py-12 text-center"
              >
                No scan yet. Submit content to see results here.
              </motion.div>
            )}
            {scan &&
              scan.status !== "completed" &&
              scan.status !== "failed" &&
              scan.status !== "rejected" && (
                <motion.div
                  key="processing"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-center py-10 sm:py-12"
                >
                  <div className="relative inline-flex">
                    <Loader2 className="w-10 h-10 mx-auto text-brand-500 animate-spin" />
                    <span className="absolute inset-0 rounded-full ring-2 ring-brand-300/40 animate-pulse-ring" />
                  </div>
                  <div className="mt-4 font-medium capitalize">
                    {scan.status.replace("_", " ")}
                  </div>
                  <div className="text-sm text-slate-500 mt-1">
                    This may take a moment for video & audio.
                  </div>
                  <div className="mt-6 h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-brand-400 via-brand-600 to-fuchsia-500 bg-[length:200%_100%] animate-shimmer"
                      style={{ width: "100%" }}
                    />
                  </div>
                </motion.div>
              )}
            {scan && scan.status === "completed" && (
              <motion.div
                key="done"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-5"
              >
                <ScoreBar
                  score={scan.score}
                  label={scan.label}
                  confidence={scan.confidence}
                />
                <div>
                  <div className="text-xs uppercase tracking-wider text-slate-500 mb-1">
                    Explanation
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {scan.explanation}
                  </p>
                </div>
                <a
                  href={`${API_URL}/report/${scan.id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary w-full"
                  onClick={async (e) => {
                    e.preventDefault();
                    const blob = await api<Blob>(ApiPaths.report(scan.id));
                    const url = URL.createObjectURL(blob as Blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `scan-${scan.id}.pdf`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Download PDF report
                </a>
              </motion.div>
            )}
            {scan &&
              (scan.status === "failed" || scan.status === "rejected") && (
                <motion.div
                  key="err"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-xl bg-rose-50 border border-rose-200 p-4 text-rose-800 text-sm"
                >
                  <div className="font-semibold capitalize mb-1">
                    {scan.status}
                  </div>
                  {scan.error_message ?? "Scan could not be completed."}
                </motion.div>
              )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
