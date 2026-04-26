import { useState } from "react";
import ProcessingStatusBoard from "../components/ProcessingStatusBoard";
import Upload from "../components/Upload";

const DEFAULT_FOLDER = "backend/data/raw_cvs";

function Processing() {
  const [folderPath, setFolderPath] = useState(DEFAULT_FOLDER);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleProcessed = () => setRefreshKey((value) => value + 1);

  return (
    <div className="grid gap-6">
      <Upload
        folderPath={folderPath}
        onFolderPathChange={setFolderPath}
        onProcessed={handleProcessed}
        onProcessingStateChange={setIsProcessing}
      />
      <ProcessingStatusBoard
        folderPath={folderPath}
        refreshKey={refreshKey}
        isProcessing={isProcessing}
      />
    </div>
  );
}

export default Processing;
