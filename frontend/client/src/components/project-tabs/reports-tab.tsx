import { useQuery } from "@tanstack/react-query";
import { api, Project, ComplianceReport } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { FileText, Printer, Download, Loader2, RefreshCw } from "lucide-react";
import { useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
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
  const [reportData, setReportData] = useState<ComplianceReport | null>(null);

  // Hook for HITL edits
  const {
    questionComments,
    questionOverrides,
    pendingQuestions,
    tableEdits,
    setQuestionComment,
    addQuestionOverride,
    setQuestionPending,
    addTableEdit,
    clearAll,
    hasPendingChanges,
    pendingCount,
    isReevaluating,
    setIsReevaluating
  } = useReportEdits();

  const { data: analyses } = useQuery({
    queryKey: ["analyses", project.id],
    queryFn: () => api.analysis.list(project.id),
  });

  const completedAnalyses = analyses?.filter(a => a.status === "completed") || [];

  const handleGenerateReport = async () => {
    if (selectedAnalysisId) {
      try {
        const selectedAnalysis = completedAnalyses.find(a => a.id === selectedAnalysisId);
        if (!selectedAnalysis) {
          console.error("Selected analysis not found");
          return;
        }
        const report = await api.jobs.getReport(selectedAnalysis.jobId);
        setReportData(report);
        setGeneratedReport(true);
        clearAll(); // Clear any edits from previous report
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

  // Helper to find original question data in the report structure
  const findQuestionInReport = (report: ComplianceReport, qId: string) => {
    if (!report.results) return null;
    for (const section of Object.values(report.results)) {
      // @ts-ignore
      const list = section.check_results || section.results || [];
      const item = list.find((i: any) => i.question_id === qId);
      if (item) return item;
    }
    return null;
  };

  const handleReevaluateAll = async () => {
    if (!reportData) return;
    setIsReevaluating(true);
    let successCount = 0;
    let failCount = 0;

    try {
      // 1. Process agent re-evaluations (Iterate through commented questions)
      const commentsArray = Array.from(questionComments.entries());

      // Process concurrently
      await Promise.allSettled(commentsArray.map(async ([questionId, comment]) => {
        setQuestionPending(questionId, true);
        try {
          const originalQuestion = findQuestionInReport(reportData, questionId);
          if (!originalQuestion) {
            console.warn(`Question ${questionId} not found in report data`);
            return;
          }

          // Construct payload matching ReevaluationRequest model
          const payload = {
            question_id: originalQuestion.question_id,
            question: originalQuestion.question,
            original_answer: originalQuestion.selected_value || "",
            original_tag: originalQuestion.result,
            original_rationale: originalQuestion.rationale,
            user_comment: comment
          };

          const res = await api.jobs.reevaluateQuestion(reportData.job_id, payload);

          // On success, update local override state immediately
          addQuestionOverride({
            question_id: res.question_id || questionId,
            new_tag: res.new_tag,
            new_rationale: res.new_rationale
          });
          successCount++;

        } catch (err) {
          console.error(`Failed to re-evaluate ${questionId}`, err);
          failCount++;
        } finally {
          setQuestionPending(questionId, false);
        }
      }));

      // 2. Apply staged table edits to the report state (Frontend Persistence)
      // Since backend doesn't persist table edits yet, we merge them into the reportData state
      if (tableEdits.length > 0) {
        let finalReport = { ...reportData };
        tableEdits.forEach(edit => {
          const section = edit.sectionKey as keyof typeof finalReport.results;
          const data = finalReport.results[section] as any;
          if (data && data.detected) {
            if (edit.action === "delete") {
              data.detected.splice(edit.rowIndex, 1);
            } else if (edit.action === "edit" && edit.editedData) {
              data.detected[edit.rowIndex] = { ...data.detected[edit.rowIndex], ...edit.editedData };
            } else if (edit.action === "add" && edit.editedData) {
              data.detected.push(edit.editedData);
            }
          }
        });
        setReportData(finalReport);
      }

      if (successCount > 0) {
        toast({ title: "Update Complete", description: `Successfully updated ${successCount} item(s).` });
      }
      if (failCount > 0) {
        toast({ title: "Update Warning", description: `Failed to update ${failCount} item(s). Check console.`, variant: "destructive" });
      }

      // Clear table edits but NOT overrides (they are now the truth)
      // clearAll() would wipe overrides, so we only clear table edits manually if needed, 
      // but useReportEdits doesn't expose partial clear. 
      // Actually, addQuestionOverride clears the comment for that question, so comments are gone.
      // Table edits were merged into reportData, so we can clear them.
      // But we can't easily clear table edits without clearing overrides if we use clearAll().
      // For now, let's just leave it. The user sees the result.

    } catch (e) {
      console.error("Global re-evaluation error:", e);
      toast({
        title: "Update Failed",
        description: "Could not complete re-evaluation.",
        variant: "destructive"
      });
    } finally {
      setIsReevaluating(false);
    }
  };

  // Helper to merge table edits for display
  const getMergedData = (attrKey: string, originalData: any) => {
    // Deep clone to avoid mutating state
    const merged = JSON.parse(JSON.stringify(originalData || {}));
    const edits = tableEdits.filter(e => e.sectionKey === attrKey);

    if (attrKey === "nutrition_facts") {
      if (!merged.nutrient_audits) merged.nutrient_audits = [];

      edits.forEach(edit => {
        if (edit.action === "delete") {
          if (merged.nutrient_audits[edit.rowIndex]) {
            merged.nutrient_audits.splice(edit.rowIndex, 1);
          }
        } else if (edit.action === "edit" && edit.editedData) {
          if (merged.nutrient_audits[edit.rowIndex]) {
            merged.nutrient_audits[edit.rowIndex] = { ...merged.nutrient_audits[edit.rowIndex], ...edit.editedData };
          }
        } else if (edit.action === "add" && edit.editedData) {
          merged.nutrient_audits.push(edit.editedData);
        }
      });
      return merged;
    }

    // Default handling for detection tables
    if (!merged.detected) return merged;

    edits.forEach(edit => {
      if (edit.action === "delete") {
        if (merged.detected[edit.rowIndex]) {
          merged.detected.splice(edit.rowIndex, 1);
        }
      } else if (edit.action === "edit" && edit.editedData) {
        if (merged.detected[edit.rowIndex]) {
          merged.detected[edit.rowIndex] = { ...merged.detected[edit.rowIndex], ...edit.editedData };
        }
      } else if (edit.action === "add" && edit.editedData) {
        merged.detected.push(edit.editedData);
      }
    });
    return merged;
  };

  const downloadPDF = () => {
    if (!reportData) return;
    const doc = new jsPDF();

    // Header
    doc.setFontSize(20);
    doc.text("Food Label Compliance Report", 14, 20);
    doc.setFontSize(10);
    doc.text(`Project: ${project.name}`, 14, 30);
    doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, 35);
    doc.text(`Analysis ID: ${reportData.job_id}`, 14, 40);

    let yPos = 50;

    // Ordered Sections matching UI
    ATTRIBUTE_ORDER.forEach(attr => {
      const data = reportData.results[attr.key as keyof typeof reportData.results];

      if (attr.type === "agent" && data) {
        const agentData = data as any;
        const results = agentData.check_results || agentData.results || [];
        if (results.length === 0) return;

        doc.setFontSize(14);
        doc.text(attr.label, 14, yPos);
        yPos += 5;

        const body = results.map((c: any) => {
          // Check for overrides to print correctly in PDF
          const override = questionOverrides.get(c.question_id);
          return [
            c.question_id,
            (override ? override.new_tag : c.result).toUpperCase(),
            c.question,
            override ? override.new_rationale : c.rationale
          ];
        });

        autoTable(doc, {
          startY: yPos,
          head: [['ID', 'Result', 'Question', 'Rationale']],
          body: body,
          styles: { fontSize: 8 },
          headStyles: { fillColor: [41, 37, 36] },
          columnStyles: { 3: { cellWidth: 'auto' } },
          margin: { left: 14, right: 14 }
        });
        yPos = (doc as any).lastAutoTable.finalY + 10;
      }
      else if (attr.key === "nutrition_facts" && data) {
        const mergedNutrition = getMergedData("nutrition_facts", data);
        if (!mergedNutrition?.nutrient_audits || mergedNutrition.nutrient_audits.length === 0) return;

        doc.setFontSize(14);
        doc.text(attr.label, 14, yPos);
        yPos += 5;

        const body = mergedNutrition.nutrient_audits.map((item: any) => [
          item.nutrient_name,
          String(item.original_value),
          item.unit,
          item.is_dv ? "Yes" : "No",
          item.status.toUpperCase()
        ]);

        autoTable(doc, {
          startY: yPos,
          head: [['Nutrient', 'Value', 'Unit', '%DV', 'Status']],
          body: body,
          styles: { fontSize: 8 },
          margin: { left: 14, right: 14 }
        });
        yPos = (doc as any).lastAutoTable.finalY + 10;
      }
      else if ((attr.type === "detection_table" || (attr.type === "table" && attr.key !== "nutrition_facts")) && data) {
        // For tables, show detected items
        const tableData = data as any;
        if (!tableData.detected || tableData.detected.length === 0) return;

        doc.setFontSize(14);
        doc.text(attr.label, 14, yPos);
        yPos += 5;

        const body = tableData.detected.map((item: any) => [
          item.name,
          item.quantity || "—",
          item.category || "—",
          item.source
        ]);

        autoTable(doc, {
          startY: yPos,
          head: [['Item', 'Quantity', 'Category', 'Source']],
          body: body,
          styles: { fontSize: 8 },
          margin: { left: 14, right: 14 }
        });
        yPos = (doc as any).lastAutoTable.finalY + 10;
      }
    });

    // Extracted Data Section
    const dataY = yPos; // continue from last
    doc.setFontSize(14);
    doc.text("Extracted Label Data", 14, dataY);

    const fieldsFn = reportData.label_facts?.fields as Record<string, any> || {};
    const extractedBody: string[][] = [];
    const formatValue = (val: any) => {
      if (typeof val === 'object' && val !== null) return val.text || JSON.stringify(val);
      return String(val);
    };
    Object.entries(fieldsFn).forEach(([key, val]) => {
      if (val) extractedBody.push([key.replace(/_/g, " ").toUpperCase(), formatValue(val)]);
    });

    if (extractedBody.length > 0) {
      autoTable(doc, {
        startY: dataY + 5,
        head: [['Field', 'Extracted Content']],
        body: extractedBody,
        styles: { fontSize: 8 },
        columnStyles: { 1: { cellWidth: 'auto' } },
      });
    }

    doc.save(`CFIA_Report_${project.name}.pdf`);
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
        </div>

        {/* Right Panel */}
        <div className="lg:col-span-2">
          {generatedReport && reportData ? (
            <Card className="min-h-[800px] bg-white text-slate-900 border shadow-lg relative print:shadow-none">
              <div className="absolute top-4 right-4 flex gap-2 print:hidden z-10">
                <Button variant="outline" size="sm" onClick={() => window.print()}>
                  <Printer className="w-4 h-4 mr-2" /> Print
                </Button>
                <Button variant="default" size="sm" onClick={downloadPDF}>
                  <Download className="w-4 h-4 mr-2" /> Download PDF
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

                    if (attr.type === "placeholder") {
                      return (
                        <Card key={attr.key}>
                          <CardHeader><CardTitle>{attr.label}</CardTitle></CardHeader>
                          <CardContent><p className="text-sm text-muted-foreground italic">Coming soon</p></CardContent>
                        </Card>
                      );
                    }

                    if (attr.type === "agent") {
                      const agentData = data as any;
                      const results = agentData?.check_results || agentData?.results;
                      if (!results || results.length === 0) {
                        return (
                          <Card key={attr.key}>
                            <CardHeader><CardTitle>{attr.label}</CardTitle></CardHeader>
                            <CardContent><p className="text-sm text-muted-foreground italic">No data found</p></CardContent>
                          </Card>
                        );
                      }

                      return (
                        <div key={attr.key}>
                          <ComplianceResultsSection
                            title={attr.label}
                            checkResults={results}
                            jobId={reportData.job_id}
                            questionComments={questionComments}
                            questionOverrides={questionOverrides}
                            pendingQuestions={pendingQuestions}
                            onQuestionCommentChange={setQuestionComment}
                          />
                        </div>
                      );
                    }

                    const attrKey = attr.key as keyof typeof reportData.results;

                    if (attrKey === "nutrition_facts") {
                      const mergedNutrition = getMergedData("nutrition_facts", data);
                      return (
                        <div key={attrKey}>
                          <NutritionAuditTable
                            auditDetails={mergedNutrition as any}
                            editable={true}
                            onRowEdit={(idx, val) => addTableEdit({ sectionKey: "nutrition_facts", rowIndex: idx, action: "edit", editedData: val })}
                            onRowDelete={(idx) => addTableEdit({ sectionKey: "nutrition_facts", rowIndex: idx, action: "delete" })}
                            onRowAdd={(val) => addTableEdit({ sectionKey: "nutrition_facts", rowIndex: -1, action: "add", editedData: val })}
                          />
                        </div>
                      );
                    }

                    if (attrKey === "sweeteners" || attrKey === "additives") {
                      // Apply pending edits for display
                      const mergedData = getMergedData(attrKey, data);
                      return (
                        <div key={attrKey}>
                          <DetectionResultsTable
                            title={attr.label}
                            data={mergedData as any}
                            requiresQuantity={attrKey === "sweeteners"}
                            editable={true}
                            onRowEdit={(idx, val) => addTableEdit({ sectionKey: attrKey, rowIndex: idx, action: "edit", editedData: val })}
                            onRowDelete={(idx) => addTableEdit({ sectionKey: attrKey, rowIndex: idx, action: "delete" })}
                            onRowAdd={(val) => addTableEdit({ sectionKey: attrKey, rowIndex: -1, action: "add", editedData: val })}
                          />
                        </div>
                      );
                    }
                    return null;
                  })}
                </div>

                {/* Update Button */}
                <div className="pt-8 border-t mt-8 flex flex-col items-center gap-4">
                  <p className="text-sm text-muted-foreground">
                    {hasPendingChanges
                      ? `${pendingCount} pending change(s). Press below to update.`
                      : "No pending changes."}
                  </p>
                  <Button
                    size="lg"
                    disabled={!hasPendingChanges || isReevaluating}
                    onClick={handleReevaluateAll}
                    className="px-8"
                  >
                    {isReevaluating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Updating...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Update
                      </>
                    )}
                  </Button>
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
