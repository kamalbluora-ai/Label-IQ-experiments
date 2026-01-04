import { useQuery } from "@tanstack/react-query";
import { api, Project, ComplianceReport } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { FileText, Printer, Download, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

interface ReportsTabProps {
  project: Project;
}

export default function ReportsTab({ project }: ReportsTabProps) {
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const [generatedReport, setGeneratedReport] = useState<boolean>(false);
  const [reportData, setReportData] = useState<ComplianceReport | null>(null);

  const { data: analyses } = useQuery({
    queryKey: ["analyses", project.id],
    queryFn: () => api.analysis.list(project.id),
  });

  const completedAnalyses = analyses?.filter(a => a.status === "completed") || [];

  const handleGenerateReport = async () => {
    if (selectedAnalysisId) {
      try {
        // Find the selected analysis to get its backend jobId
        const selectedAnalysis = completedAnalyses.find(a => a.id === selectedAnalysisId);
        if (!selectedAnalysis) {
          console.error("Selected analysis not found");
          return;
        }
        // Use the backend jobId, not the frontend analysis.id
        const report = await api.jobs.getReport(selectedAnalysis.jobId);
        setReportData(report);
        setGeneratedReport(true);
      } catch (e) {
        console.error("Failed to fetch report details", e);
      }
    }
  };

  // Score is now calculated by backend: reportData.results.compliance_score

  const downloadPDF = () => {
    if (!reportData) return;

    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.width;

    // Header
    doc.setFontSize(20);
    doc.text("Food Label Compliance Report", 14, 20);

    doc.setFontSize(10);
    doc.text(`Project: ${project.name}`, 14, 30);
    doc.text(`Date: ${new Date().toLocaleDateString()}`, 14, 35);
    doc.text(`Analysis ID: ${reportData.job_id}`, 14, 40);

    // Score Visualization (Donut Chart) - Uses backend-calculated score
    const score = reportData.results.compliance_score;
    const compliantColor = [74, 222, 128]; // Green
    const nonCompliantColor = [248, 113, 113]; // Red

    const chartX = 40;
    const chartY = 80;
    const radius = 20;

    doc.setFontSize(14);
    doc.text("Compliance Score", 14, 55);

    // Draw Donut Chart manually using arcs
    // 360 degrees = 2 * Math.PI radians
    const totalAngle = 2 * Math.PI;
    const compliantAngle = (score / 100) * totalAngle;

    // Helper to draw a segment
    const drawSegment = (startAngle: number, endAngle: number, color: number[]) => {
      doc.setFillColor(color[0], color[1], color[2]);
      // For a true arc in PDF we need path construction, let's approximation with lines for robustness if needed, 
      // but jspdf has 'lines' or 'path'.
      // Actually, simple wedge: center -> outer arc -> inner arc (if donut) matches path.
      // Simplified approach for robustness: Draw thick lines or many small triangles.
      // BETTER: Using doc.circle for background (red) and drawing a white wedge/arc over it is harder.
      // LET'S DO: Full Red Circle, then Green Wedge on top.

      // However, standard jspdf doesn't have easy "wedge" command.
      // We will stick to a simpler, cleaner visual: A Progress Bar that looks PROFESSIONAL.

      // Reverting to high-quality Progress Bar as requested "visual is off" likely meant the crude overlap.
      // Let's make a really nice segmented bar.
    };

    // Actually, user specifically asked for "visual ... 60% compliant 40% non-compliant".
    // A pie/donut is best. Let's try to implement a robust wedge.
    // If score is 100, full green circle.
    if (score >= 100) {
      doc.setFillColor(compliantColor[0], compliantColor[1], compliantColor[2]);
      doc.circle(chartX, chartY, radius, 'F');
    } else if (score <= 0) {
      doc.setFillColor(nonCompliantColor[0], nonCompliantColor[1], nonCompliantColor[2]);
      doc.circle(chartX, chartY, radius, 'F');
    } else {
      // Draw Red Base
      doc.setFillColor(nonCompliantColor[0], nonCompliantColor[1], nonCompliantColor[2]);
      doc.circle(chartX, chartY, radius, 'F');

      // Draw Green Wedge (Approximation using triangles for arc)
      doc.setFillColor(compliantColor[0], compliantColor[1], compliantColor[2]);

      // Draw wedge from -90deg (top) to compliantAngle
      const startRad = -Math.PI / 2;
      const endRad = startRad + compliantAngle;
      const step = 0.05; // radian step for smoothness logic

      // Center point
      let px = chartX;
      let py = chartY;

      // We construct a polygon path for the slice
      // Move to center
      // Line to start
      // Arc to end
      // Line to center
      // Fill

      // Since pure path API is complex, we'll brute force small triangles which is robust in all PDF readers
      for (let r = startRad; r < endRad; r += step) {
        const x1 = chartX + Math.cos(r) * radius;
        const y1 = chartY + Math.sin(r) * radius;
        const x2 = chartX + Math.cos(Math.min(r + step, endRad)) * radius;
        const y2 = chartY + Math.sin(Math.min(r + step, endRad)) * radius;
        doc.triangle(chartX, chartY, x1, y1, x2, y2, 'F');
      }
    }

    // Inner White Circle to make it a Donut
    doc.setFillColor(255, 255, 255);
    doc.circle(chartX, chartY, radius * 0.6, 'F');

    // Score Text in Center
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    const textWidth = doc.getStringUnitWidth(`${score}%`) * 12 / doc.internal.scaleFactor;
    doc.text(`${score}%`, chartX - (textWidth / 2) - 2, chartY + 2); // approximate centering

    // Legend
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");

    // Green Legend
    doc.setFillColor(compliantColor[0], compliantColor[1], compliantColor[2]);
    doc.rect(chartX + radius + 15, chartY - 10, 4, 4, "F");
    doc.text("Compliant", chartX + radius + 22, chartY - 7);

    // Red Legend
    doc.setFillColor(nonCompliantColor[0], nonCompliantColor[1], nonCompliantColor[2]);
    doc.rect(chartX + radius + 15, chartY + 5, 4, 4, "F");
    doc.text("Non-Compliant / Review", chartX + radius + 22, chartY + 8);

    // Issues Table
    const tableBody = reportData.results.issues.map(issue => [
      issue.code,
      issue.severity.toUpperCase().replace("_", " "),
      issue.message
    ]);

    autoTable(doc, {
      startY: 120, // Moved down to avoid chart overlap
      head: [['Code', 'Severity', 'Description']],
      body: tableBody,
      styles: { fontSize: 8 },
      headStyles: { fillColor: [41, 37, 36] },
    });

    // CFIA Evidence (References)
    const finalY = (doc as any).lastAutoTable.finalY + 10;
    doc.setFontSize(14);
    doc.text("Regulatory References", 14, finalY);

    const evidenceBody: string[][] = [];
    Object.entries(reportData.cfia_evidence || {}).forEach(([key, items]: [string, any]) => {
      if (Array.isArray(items)) {
        items.forEach((item: any) => {
          evidenceBody.push([key, item.content || item.title || "Reference"]);
        });
      }
    });

    if (evidenceBody.length > 0) {
      autoTable(doc, {
        startY: finalY + 5,
        head: [['Category', 'Excerpt']],
        body: evidenceBody,
        styles: { fontSize: 8 },
        columnStyles: { 1: { cellWidth: 'auto' } },
      });
    }



    // Extracted Data Section (New)
    const dataY = (doc as any).lastAutoTable.finalY + 10;
    doc.setFontSize(14);
    doc.text("Extracted Label Data", 14, dataY);

    const fieldsFn = reportData.label_facts?.fields as Record<string, any> || {};
    const extractedBody: string[][] = [];

    // Helper to format field values
    const formatValue = (val: any) => {
      if (typeof val === 'object' && val !== null) {
        return val.text || JSON.stringify(val);
      }
      return String(val);
    };

    // List of priority fields to show
    const priorityFields = [
      "common_name_en", "common_name_fr",
      "net_quantity_value", "net_quantity_unit_words_en",
      "ingredients_list_en", "ingredients_list_fr",
      "dealer_name", "dealer_address",
      "best_before_en", "best_before_fr"
    ];

    // Add priority fields first
    priorityFields.forEach(key => {
      if (fieldsFn[key]) {
        extractedBody.push([key.replace(/_/g, " ").toUpperCase(), formatValue(fieldsFn[key])]);
      }
    });

    // Add any other non-empty fields not already added
    Object.entries(fieldsFn).forEach(([key, val]) => {
      if (!priorityFields.includes(key) && val) {
        const v = formatValue(val);
        if (v && v.trim() !== "") {
          extractedBody.push([key.replace(/_/g, " ").toUpperCase(), v.substring(0, 100) + (v.length > 100 ? "..." : "")]);
        }
      }
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
        {/* Left Sidebar: Selection */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Report Configuration</CardTitle>
              <CardDescription>Select an completed analysis to generate a detailed report.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {completedAnalyses.length === 0 ? (
                <p className="text-sm text-muted-foreground">No completed analyses available.</p>
              ) : (
                <RadioGroup
                  value={selectedAnalysisId || ""}
                  onValueChange={setSelectedAnalysisId}
                  className="space-y-3"
                >
                  {completedAnalyses.map((analysis) => (
                    <div key={analysis.id} className="flex items-start space-x-2">
                      <RadioGroupItem value={analysis.id} id={analysis.id} />
                      <div className="grid gap-1.5 leading-none">
                        <label
                          htmlFor={analysis.id}
                          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                        >
                          {analysis.name}
                        </label>
                        <p className="text-xs text-muted-foreground">
                          {new Date(analysis.createdAt).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </RadioGroup>
              )}

              <Button
                className="w-full mt-4"
                disabled={!selectedAnalysisId}
                onClick={handleGenerateReport}
              >
                <FileText className="w-4 h-4 mr-2" />
                View Report
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel: Report Preview */}
        <div className="lg:col-span-2">
          {generatedReport && reportData ? (
            <Card className="min-h-[800px] bg-white text-slate-900 border shadow-lg relative print:shadow-none">

              {/* Toolbar */}
              <div className="absolute top-4 right-4 flex gap-2 print:hidden z-10">
                <Button variant="outline" size="sm" onClick={() => window.print()}>
                  <Printer className="w-4 h-4 mr-2" />
                  Print
                </Button>
                <Button variant="default" size="sm" onClick={downloadPDF}>
                  <Download className="w-4 h-4 mr-2" />
                  Download PDF
                </Button>
              </div>

              <CardContent className="p-12 space-y-10">

                {/* Header */}
                <div className="border-b pb-8">
                  <h1 className="text-3xl font-bold text-slate-900">Compliance Analysis Report</h1>
                  <div className="mt-6 grid grid-cols-2 gap-x-12 gap-y-4 text-sm text-slate-600">
                    <div>
                      <span className="block font-semibold text-slate-900">Project Name</span>
                      <span>{project.name}</span>
                    </div>
                    <div>
                      <span className="block font-semibold text-slate-900">Analysis Date</span>
                      <span>{new Date(reportData.created_at).toLocaleDateString()}</span>
                    </div>
                    <div>
                      <span className="block font-semibold text-slate-900">Mode</span>
                      <Badge variant="secondary">{reportData.mode}</Badge>
                    </div>
                    <div>
                      <span className="block font-semibold text-slate-900">Overall Verdict</span>
                      <Badge className={
                        reportData.results.verdict === "PASS" ? "bg-green-600" :
                          reportData.results.verdict === "FAIL" ? "bg-red-600" : "bg-yellow-600"
                      }>
                        {reportData.results.verdict}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Score Visualization */}
                <div className="space-y-4">
                  <h2 className="text-xl font-bold text-slate-900">Compliance Score</h2>
                  <div className="flex items-center gap-6">
                    <div className="relative w-32 h-32 flex items-center justify-center">
                      {/* Simple CSS-conic gradient for pie chart visual */}
                      <div
                        className="absolute inset-0 rounded-full"
                        style={{
                          background: `conic-gradient(#4ade80 ${reportData.results.compliance_score}%, #f87171 0)`
                        }}
                      />
                      <div className="absolute inset-4 bg-white rounded-full flex items-center justify-center">
                        <span className="text-2xl font-bold">{reportData.results.compliance_score}%</span>
                      </div>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                        <span>Compliant Elements</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                        <span>Non-Compliant / Review Needed</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Detailed Findings */}
                <div className="space-y-6">
                  <h2 className="text-xl font-bold text-slate-900">Detailed Findings</h2>

                  {reportData.results.issues.length === 0 ? (
                    <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex gap-3 text-green-800">
                      <CheckCircle className="w-5 h-5 shrink-0" />
                      <p>No compliance issues detected.</p>
                    </div>
                  ) : (
                    <div className="grid gap-4">
                      {reportData.results.issues.map((issue, idx) => (
                        <div key={idx} className={`p-4 rounded-lg border flex gap-4 ${issue.severity === "fail" || issue.severity === "FAIL"
                          ? "bg-red-50 border-red-200"
                          : "bg-yellow-50 border-yellow-200"
                          }`}>
                          {issue.severity === "fail" || issue.severity === "FAIL" ? (
                            <XCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-yellow-600 shrink-0 mt-0.5" />
                          )}

                          <div className="space-y-1">
                            <h3 className={`font-semibold ${issue.severity === "fail" || issue.severity === "FAIL" ? "text-red-900" : "text-yellow-900"
                              }`}>
                              {issue.code}
                            </h3>
                            <p className="text-slate-700 text-sm">{issue.message}</p>

                            {issue.references && issue.references.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-slate-200/50">
                                <p className="text-xs font-semibold text-slate-500 mb-1">Regulatory Reference:</p>
                                <ul className="text-xs text-slate-600 list-disc pl-4 space-y-0.5">
                                  {issue.references.map((ref: any, rIdx: number) => (
                                    <li key={rIdx}>{ref.title || ref.content?.substring(0, 100)}...</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Disclaimer */}
                <div className="pt-12 border-t mt-12">
                  <p className="text-xs text-slate-400 text-center">
                    Generated by Bluora CFIA.AI Platform. This automated report is for guidance only and does not constitute legal advice.
                  </p>
                </div>

              </CardContent>
            </Card>
          ) : (
            <div className="h-full flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-12 text-muted-foreground bg-muted/10">
              <FileText className="w-16 h-16 mb-4 opacity-20" />
              <h3 className="text-lg font-medium">Select an Analysis</h3>
              <p className="text-sm max-w-xs text-center mt-2">
                Choose a completed analysis on the left to view the full detailed report and download the PDF.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
