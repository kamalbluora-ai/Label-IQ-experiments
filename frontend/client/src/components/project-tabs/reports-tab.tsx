
import { useQuery } from "@tanstack/react-query";
import { api, Project, ComplianceReport } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { FileText, Printer, Download, Loader2, RefreshCw, Save } from "lucide-react";
import { useState } from "react";
import { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, BorderStyle } from "docx";
import { saveAs } from "file-saver";
import NutritionAuditTable from "@/components/NutritionAuditTable";
import ComplianceResultsSection from "@/components/ComplianceResultsSection";
import DetectionResultsTable, { DetectedItem } from "@/components/DetectionResultsTable";
import { useReportEdits } from "@/hooks/useReportEdits";
import { useToast } from "@/hooks/use-toast";

// Define the fixed order of all 12 attribute sections
const ATTRIBUTE_ORDER = [
  { key: "bilingual", label: "Bilingual labelling", type: "agent" },
  { key: "common_name", label: "Common name", type: "agent" },
  { key: "country_origin", label: "Country of Origin", type: "agent" },
  { key: "date_marking", label: "Date marking and storage instructions", type: "agent" },
  { key: "irradiation", label: "Irradiation foods", type: "agent" },
  { key: "ingredients", label: "List of ingredients and allergens", type: "agent" },
  { key: "nutrition_facts", label: "Net quantity, Nutrient labelling", type: "table" },
  { key: "sweeteners", label: "Sweeteners", type: "detection_table" },
  { key: "additives", label: "Food additives", type: "detection_table" },
  { key: "allergens_glutens", label: "Allergens and glutens", type: "placeholder" },
  { key: "health_claim", label: "Health claims, nutrient claims", type: "placeholder" },
  { key: "claim_tag", label: "Method of production, Organic", type: "agent" },
] as const;

interface ReportsTabProps {
  project: Project;
}

export default function ReportsTab({ project }: ReportsTabProps) {
  const { toast } = useToast();
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const [generatedReport, setGeneratedReport] = useState<boolean>(false);

  // Local mutable copy of the report for editing
  const [reportData, setReportData] = useState<ComplianceReport | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);

  // New Hook for Layout Edits
  const {
    tagOverrides,
    userComments,
    modifiedQuestions,
    setTagOverride,
    setUserComment,
    clearAll,
    hasPendingChanges,
    pendingCount
  } = useReportEdits();

  const { data: analyses } = useQuery({
    queryKey: ["analyses", project.id],
    queryFn: () => api.analysis.list(project.id),
  });

  const completedAnalyses = analyses?.filter(a => a.status === "completed") || [];

  // Fetch job images when reportData is available
  const { data: jobImages } = useQuery({
    queryKey: ["job-images", reportData?.job_id],
    queryFn: () => api.jobs.getImages(reportData!.job_id),
    enabled: !!reportData,
  });

  const handleGenerateReport = async () => {
    if (selectedAnalysisId) {
      try {
        const selectedAnalysis = completedAnalyses.find(a => a.id === selectedAnalysisId);
        if (!selectedAnalysis) return;

        const report = await api.jobs.getReport(selectedAnalysis.jobId);
        setReportData(report);
        setGeneratedReport(true);
        clearAll(); // Clear previous edits
      } catch (e) {
        console.error("Failed to fetch report details", e);
        toast({
          title: "Error",
          description: "Failed to load report.",
          variant: "destructive"
        });
      }
    }
  };

  // --- Handlers ---

  const handleTableUpdate = (sectionKey: string, newData: any) => {
    if (!reportData) return;
    setReportData(prev => {
      if (!prev) return null;
      const newReport = { ...prev };
      // @ts-ignore
      newReport.results[sectionKey] = newData;
      return newReport;
    });
  };

  const handleSave = () => {
    if (!reportData) return;

    // Guard: no-op if no pending changes
    if (!hasPendingChanges) {
      toast({ title: "Info", description: "No changes to save." });
      return;
    }

    const newReport = JSON.parse(JSON.stringify(reportData));

    // Merge tag overrides
    tagOverrides.forEach((override, qId) => {
      Object.values(newReport.results).forEach((section: any) => {
        const list = section.check_results || section.results;
        if (Array.isArray(list)) {
          const item = list.find((i: any) => i.question_id === qId);
          if (item) item.result = override.new_tag;
        }
      });
    });

    // Merge user comments
    userComments.forEach((comment, qId) => {
      Object.values(newReport.results).forEach((section: any) => {
        const list = section.check_results || section.results;
        if (Array.isArray(list)) {
          const item = list.find((i: any) => i.question_id === qId);
          if (item) item.user_comment = comment.comment;
        }
      });
    });

    setReportData(newReport);
    clearAll();
    toast({ title: "Success", description: "Changes saved." });
  };

  const handleUpdate = async () => {
    if (!reportData || !hasPendingChanges) return;

    setIsUpdating(true);
    try {
      // 1. Build payload from current pending changes BEFORE clearing
      const payload: any[] = [];
      modifiedQuestions.forEach(qId => {
        const tag = tagOverrides.get(qId);
        const comment = userComments.get(qId);

        if (tag || comment) {
          payload.push({
            question_id: qId,
            new_tag: tag?.new_tag,
            user_comment: comment?.comment
          });
        }
      });

      // 2. Apply local changes (merges into reportData, clears maps)
      handleSave();

      // 3. Send to backend
      if (payload.length > 0) {
        await api.jobs.saveReportEdits(reportData.job_id, payload);
        toast({ title: "Success", description: "Report updated and synced to cloud." });
      }

    } catch (e) {
      console.error(e);
      toast({ title: "Error", description: "Failed to sync report.", variant: "destructive" });
    } finally {
      setIsUpdating(false);
    }
  };


  const downloadDOCX = async () => {
    if (!reportData) return;

    try {
      const sections = [];

      // Header
      sections.push(
        new Paragraph({
          children: [
            new TextRun({ text: "Food Label Compliance Report", bold: true, size: 28 })
          ],
          spacing: { after: 400 }
        }),
        new Paragraph({ text: `Project: ${project.name}` }),
        new Paragraph({ text: `Date: ${new Date().toLocaleDateString()}` }),
        new Paragraph({ text: `Analysis ID: ${reportData.job_id}`, spacing: { after: 400 } })
      );

      // Compliance Sections
      ATTRIBUTE_ORDER.forEach(attr => {
        const data = reportData.results[attr.key as keyof typeof reportData.results];
        if (attr.type === "agent") {
          const agentData = data as any;
          const results = agentData?.check_results || agentData?.results;
          if (results && results.length > 0) {
            sections.push(
              new Paragraph({
                text: attr.label,
                heading: "Heading2",
                spacing: { before: 400, after: 200 }
              })
            );

            results.forEach((check: any) => {
              // Apply local overrides if they exist (though handleSave should have merged them)
              const override = tagOverrides.get(check.question_id);
              const result = override ? override.new_tag : check.result;
              const comment = userComments.get(check.question_id)?.comment || check.user_comment;

              sections.push(
                new Paragraph({
                  children: [
                    new TextRun({ text: "Question: ", bold: true }),
                    new TextRun({ text: check.question })
                  ]
                }),
                new Paragraph({
                  children: [
                    new TextRun({ text: "Result: ", bold: true }),
                    new TextRun({
                      text: result.toUpperCase(),
                      color: result === "pass" ? "008000" : result === "fail" ? "FF0000" : "FFA500"
                    })
                  ]
                }),
                new Paragraph({
                  children: [
                    new TextRun({ text: "Rationale: ", bold: true }),
                    new TextRun({ text: check.rationale })
                  ]
                })
              );

              if (comment) {
                sections.push(
                  new Paragraph({
                    children: [
                      new TextRun({ text: "User Comment: ", bold: true, color: "0000FF" }),
                      new TextRun({ text: comment, italics: true })
                    ],
                    spacing: { before: 100 }
                  })
                );
              }

              sections.push(new Paragraph({ text: "", spacing: { after: 200 } })); // Spacer
            });
          }
        }
      });

      const doc = new Document({
        sections: [{
          properties: {},
          children: sections,
        }],
      });

      const blob = await Packer.toBlob(doc);
      saveAs(blob, `Compliance_Report_${reportData.job_id}.docx`);
      toast({ title: "Success", description: "Report downloaded as DOCX" });

    } catch (e) {
      console.error(e);
      toast({ title: "Error", description: "Failed to generate DOCX.", variant: "destructive" });
    }
  };

  return (
    <div className="space-y-8">
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Report Configuration</CardTitle>
              <CardDescription>Select an analysis to view report.</CardDescription>
            </CardHeader>
            <CardContent>
              {completedAnalyses.length === 0 ? (
                <p className="text-sm text-muted-foreground">No completed analyses available.</p>
              ) : (
                <RadioGroup value={selectedAnalysisId || ""} onValueChange={setSelectedAnalysisId}>
                  {completedAnalyses.map((analysis) => (
                    <div key={analysis.id} className="flex items-center space-x-2 py-2">
                      <RadioGroupItem value={analysis.id} id={analysis.id} />
                      <label htmlFor={analysis.id} className="text-sm font-medium cursor-pointer">
                        {analysis.name}
                      </label>
                    </div>
                  ))}
                </RadioGroup>
              )}
              <Button className="w-full mt-4" disabled={!selectedAnalysisId} onClick={handleGenerateReport}>
                <FileText className="w-4 h-4 mr-2" /> View Report
              </Button>
            </CardContent>
          </Card>

          {/* Label Images Card */}
          {reportData && jobImages && jobImages.images.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Label Images</CardTitle>
                <CardDescription>{jobImages.images.length} image(s)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {jobImages.images.map((img, idx) => (
                    <div key={idx} className="relative aspect-square rounded border overflow-hidden bg-muted">
                      <img
                        src={`${import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"}/v1/jobs/${reportData.job_id}/images/${idx}`}
                        alt={img.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Panel */}
        <div className="lg:col-span-2">
          {generatedReport && reportData ? (
            <Card className="min-h-[800px] bg-white text-slate-900 border shadow-lg relative print:shadow-none">
              <div className="absolute top-4 right-4 flex gap-2 print:hidden z-10">
                <Button variant="outline" size="sm" onClick={() => window.print()}>
                  <Printer className="w-4 h-4 mr-2" /> Print
                </Button>
                <Button variant="default" size="sm" onClick={downloadDOCX}>
                  <Download className="w-4 h-4 mr-2" /> Download DOCX
                </Button>
              </div>

              <CardContent className="p-12 space-y-10">
                <div className="border-b pb-8">
                  <h1 className="text-3xl font-bold text-slate-900">{project.name}</h1>
                </div>

                <div className="space-y-6">
                  <h2 className="text-xl font-bold text-slate-900">Compliance Results</h2>

                  {ATTRIBUTE_ORDER.map(attr => {
                    const data = reportData.results[attr.key as keyof typeof reportData.results];

                    if (attr.type === "placeholder") return null;

                    if (attr.type === "agent") {
                      const agentData = data as any;
                      const results = agentData?.check_results || agentData?.results;
                      if (!results || results.length === 0) {
                        return null;
                      }

                      return (
                        <div key={attr.key}>
                          <ComplianceResultsSection
                            title={attr.label}
                            checkResults={results}
                            tagOverrides={tagOverrides}
                            onTagChange={setTagOverride}
                            userComments={userComments}
                            onUserCommentChange={setUserComment}
                            modifiedQuestions={modifiedQuestions}
                          />
                        </div>
                      );
                    }

                    const attrKey = attr.key as keyof typeof reportData.results;

                    if (attrKey === "nutrition_facts") {
                      return (
                        <div key={attrKey}>
                          <NutritionAuditTable
                            auditDetails={data as any}
                            editable={true}
                            onUpdate={(newData) => handleTableUpdate("nutrition_facts", newData)}
                          />
                        </div>
                      );
                    }

                    if (attrKey === "sweeteners" || attrKey === "additives") {
                      return (
                        <div key={attrKey}>
                          <DetectionResultsTable
                            title={attr.label}
                            data={data as any}
                            requiresQuantity={attrKey === "sweeteners"}
                            editable={true}
                            onUpdate={(newData) => handleTableUpdate(attrKey, newData)}
                          />
                        </div>
                      );
                    }
                    return null;
                  })}
                </div>

                {/* Save & Update Buttons */}
                <div className="pt-8 border-t mt-8 flex flex-col items-center gap-4">
                  <p className="text-sm text-muted-foreground">
                    {hasPendingChanges
                      ? `${pendingCount} pending change(s). Press 'Update' to sync changes.`
                      : "All changes saved."}
                  </p>
                  <div className="flex gap-4">
                    <Button
                      size="lg"
                      variant="outline"
                      onClick={handleSave}
                      className="px-8"
                    >
                      <Save className="w-4 h-4 mr-2" />
                      Save
                    </Button>
                    <Button
                      size="lg"
                      disabled={!hasPendingChanges || isUpdating}
                      onClick={handleUpdate}
                      className="px-8"
                    >
                      {isUpdating ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4 mr-2" />
                      )}
                      Update
                    </Button>
                  </div>
                </div>

                <div className="pt-12 border-t mt-12">
                  <p className="text-xs text-slate-400 text-center">Generated by Bluora CFIA.AI Platform.</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="h-full flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-12 text-muted-foreground bg-muted/10">
              <FileText className="w-16 h-16 mb-4 opacity-20" />
              <h3 className="text-lg font-medium">Select an Analysis</h3>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
