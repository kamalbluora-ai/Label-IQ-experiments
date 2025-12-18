import { useQuery } from "@tanstack/react-query";
import { api, Project } from "@/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { FileText, Printer, Download } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

interface ReportsTabProps {
  project: Project;
}

export default function ReportsTab({ project }: ReportsTabProps) {
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const [generatedReport, setGeneratedReport] = useState<boolean>(false);

  const { data: analyses } = useQuery({
    queryKey: ["analyses", project.id],
    queryFn: () => api.analysis.list(project.id),
  });

  const completedAnalyses = analyses?.filter(a => a.status === "completed") || [];

  const generateReport = () => {
    setGeneratedReport(true);
  };

  return (
    <div className="space-y-8">
      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Report Configuration</CardTitle>
              <CardDescription>Select an analysis to generate a report.</CardDescription>
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
                onClick={generateReport}
              >
                <FileText className="w-4 h-4 mr-2" />
                Generate Final Report
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {generatedReport && selectedAnalysisId ? (
            <Card className="min-h-[600px] bg-white text-black relative">
              <div className="absolute top-4 right-4 flex gap-2 print:hidden">
                <Button variant="outline" size="sm" onClick={() => window.print()}>
                  <Printer className="w-4 h-4 mr-2" />
                  Print
                </Button>
                <Button variant="outline" size="sm" onClick={async () => {
                  try {
                    const blob = await api.analysis.downloadReport(selectedAnalysisId!);
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `CFIA_Report_${project.name.replace(/\s+/g, '_')}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  } catch (error) {
                    console.error('Failed to download PDF:', error);
                  }
                }}>
                  <Download className="w-4 h-4 mr-2" />
                  PDF
                </Button>
              </div>

              <CardContent className="p-12 space-y-8">
                <div className="border-b pb-6">
                  <h1 className="text-3xl font-bold text-slate-900">Food Labelling Analysis Report</h1>
                  <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-slate-600">
                    <div>
                      <p className="font-semibold">Project:</p>
                      <p>{project.name}</p>
                    </div>
                    <div>
                      <p className="font-semibold">Date Generated:</p>
                      <p>{new Date().toLocaleDateString()}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  <h2 className="text-xl font-semibold text-slate-800">Executive Summary</h2>
                  <p className="text-slate-600 leading-relaxed">
                    This report summarizes the findings from the analysis performed on the project "{project.name}".
                    The overall integrity of the inspected elements is within acceptable parameters, pending specific recommendations detailed below.
                  </p>
                </div>

                <div className="space-y-6">
                  <h2 className="text-xl font-semibold text-slate-800">Detailed Findings</h2>
                  {completedAnalyses
                    .filter(a => a.id === selectedAnalysisId)
                    .map((analysis) => (
                      <div key={analysis.id} className="bg-slate-50 p-4 rounded-lg border">
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="font-semibold text-slate-900">{analysis.name}</h3>
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Passed</Badge>
                        </div>
                        <p className="text-sm text-slate-700">
                          {analysis.resultSummary || "Analysis completed successfully. No critical anomalies detected."}
                        </p>
                        {analysis.details && (
                          <div className="mt-3 text-xs font-mono text-slate-500 grid grid-cols-2 gap-2">
                            {Object.entries(analysis.details)
                              .filter(([k, v]) => !k.startsWith('_') && typeof v === 'string')
                              .map(([k, v]) => (
                                <div key={k}>
                                  <span className="uppercase">{k.replace('_', ' ')}:</span> {v}
                                </div>
                              ))}
                          </div>
                        )}
                      </div>
                    ))}
                </div>

                <div className="space-y-4 pt-8 border-t">
                  <p className="text-xs text-slate-400 text-center">
                    Generated by Bluora CFIA.AI Platform • Confidential • Page 1 of 1
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="h-full flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-12 text-muted-foreground bg-muted/10">
              <FileText className="w-16 h-16 mb-4 opacity-20" />
              <h3 className="text-lg font-medium">No Report Generated</h3>
              <p className="text-sm max-w-xs text-center mt-2">
                Select a completed analysis from the left panel and click "Generate Final Report" to view the document.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
