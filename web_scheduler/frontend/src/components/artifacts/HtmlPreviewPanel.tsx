import { artifactPreviewUrl } from "../../api/artifacts";

function HtmlPreviewPanel({ artifactId }: { artifactId: number | null }) {
  if (!artifactId) {
    return <div className="state-box">Select artifact to preview</div>;
  }

  return (
    <div className="preview-panel">
      <iframe title="html-preview" src={artifactPreviewUrl(artifactId)} className="preview-iframe" />
    </div>
  );
}

export default HtmlPreviewPanel;
