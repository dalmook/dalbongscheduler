import type { Artifact } from "../../types/artifact";
import { getArtifactPreviewUrl } from "../../api/artifacts";

function HtmlPreviewPanel({ artifact }: { artifact: Artifact | null }) {
  if (!artifact) return <div className="state">Select artifact to preview</div>;

  if (artifact.artifact_type === "html") {
    return (
      <div className="preview-wrap">
        <iframe className="preview-iframe" src={getArtifactPreviewUrl(artifact.id)} title="preview" />
      </div>
    );
  }

  const text = artifact.content_text || artifact.content_json || "(no preview content)";
  return (
    <div className="card">
      <pre>{text}</pre>
    </div>
  );
}

export default HtmlPreviewPanel;
