import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import type { PaginatedResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ChevronLeft, ChevronRight, Search, Eye } from "lucide-react";

interface CaseRecord {
  id: string;
  transfer_id: string;
  case_date: string;
  donor_tag: string;
  sire_name: string;
  recipient_tag: string;
  protocol_name: string;
  outcome: "pregnant" | "open" | "recheck" | "pending";
  pregnancy_prediction_probability: number;
  actual_result: string | null;
  technician_name: string;
  embryo_grade: string;
  cl_size_mm: number;
  notes: string;
  follow_up_date: string | null;
}

interface CaseFilter {
  search: string;
  outcome: string;
  protocol: string;
  dateFrom: string;
  dateTo: string;
}

export default function CaseRecordsPage() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<CaseFilter>({
    search: "",
    outcome: "",
    protocol: "",
    dateFrom: "",
    dateTo: "",
  });

  const pageSize = 25;

  // Fetch cases
  useEffect(() => {
    fetchCases();
  }, [page, filter]);

  const fetchCases = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (filter.search) params.append("search", filter.search);
      if (filter.outcome) params.append("outcome", filter.outcome);
      if (filter.protocol) params.append("protocol", filter.protocol);
      if (filter.dateFrom) params.append("date_from", filter.dateFrom);
      if (filter.dateTo) params.append("date_to", filter.dateTo);

      const response = await api.get<PaginatedResponse<CaseRecord>>(`/cases?${params}`);
      setCases(response.data.items);
      setTotal(response.data.total);
      setPages(response.data.pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setFilter({ ...filter, search: value });
    setPage(1);
  };

  const handleFilterChange = (key: keyof CaseFilter, value: string) => {
    setFilter({ ...filter, [key]: value });
    setPage(1);
  };

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case "pregnant":
        return "bg-green-100 text-green-800";
      case "open":
        return "bg-red-100 text-red-800";
      case "recheck":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getPredictionColor = (prob: number) => {
    if (prob < 0.3) return "text-red-600";
    if (prob < 0.6) return "text-yellow-600";
    return "text-green-600";
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Case Records & Traceability</h1>
        <p className="text-gray-600">Browse and track all ET transfer cases</p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filter Cases</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Search</label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                  <Input
                    placeholder="Search by transfer ID, donor, recipient..."
                    value={filter.search}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Outcome</label>
              <Select
                value={filter.outcome}
                onValueChange={(value) => handleFilterChange("outcome", value)}
              >
                <option value="">All Outcomes</option>
                <option value="pregnant">Pregnant</option>
                <option value="open">Open</option>
                <option value="recheck">Recheck</option>
                <option value="pending">Pending</option>
              </Select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Protocol</label>
              <Input
                placeholder="Filter by protocol..."
                value={filter.protocol}
                onChange={(e) => handleFilterChange("protocol", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Date Range</label>
              <div className="flex gap-2">
                <Input
                  type="date"
                  value={filter.dateFrom}
                  onChange={(e) => handleFilterChange("dateFrom", e.target.value)}
                  className="flex-1"
                />
                <Input
                  type="date"
                  value={filter.dateTo}
                  onChange={(e) => handleFilterChange("dateTo", e.target.value)}
                  className="flex-1"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setFilter({ search: "", outcome: "", protocol: "", dateFrom: "", dateTo: "" });
                setPage(1);
              }}
            >
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-gray-600">Total Cases</p>
              <p className="text-3xl font-bold">{total}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-gray-600">Current Page</p>
              <p className="text-3xl font-bold">
                {page} / {pages}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-gray-600">Page Size</p>
              <p className="text-3xl font-bold">{pageSize}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-gray-600">Showing</p>
              <p className="text-3xl font-bold">
                {Math.min((page - 1) * pageSize + 1, total)}-
                {Math.min(page * pageSize, total)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cases Table */}
      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <p className="text-gray-600">Loading cases...</p>
            </div>
          ) : cases.length === 0 ? (
            <div className="flex items-center justify-center h-40">
              <p className="text-gray-600">No cases found</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Transfer ID</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Donor / Sire</TableHead>
                      <TableHead>Recipient</TableHead>
                      <TableHead>Protocol</TableHead>
                      <TableHead>Prediction</TableHead>
                      <TableHead>Outcome</TableHead>
                      <TableHead>Grade</TableHead>
                      <TableHead>CL Size</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cases.map((caseRecord) => (
                      <TableRow key={caseRecord.id} className="hover:bg-gray-50">
                        <TableCell className="font-mono text-sm">{caseRecord.transfer_id}</TableCell>
                        <TableCell className="text-sm">
                          {new Date(caseRecord.case_date).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-sm">
                          <div>{caseRecord.donor_tag}</div>
                          <div className="text-xs text-gray-500">{caseRecord.sire_name}</div>
                        </TableCell>
                        <TableCell className="text-sm">{caseRecord.recipient_tag}</TableCell>
                        <TableCell className="text-sm">{caseRecord.protocol_name}</TableCell>
                        <TableCell>
                          <span className={`font-bold ${getPredictionColor(caseRecord.pregnancy_prediction_probability)}`}>
                            {(caseRecord.pregnancy_prediction_probability * 100).toFixed(0)}%
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge className={getOutcomeColor(caseRecord.outcome)}>
                            {caseRecord.outcome}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">{caseRecord.embryo_grade}</TableCell>
                        <TableCell className="text-sm">{caseRecord.cl_size_mm} mm</TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => navigate(`/app/cases/${caseRecord.id}`)}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <Button
                  variant="outline"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Previous
                </Button>

                <div className="text-sm text-gray-600">
                  Page {page} of {pages}
                </div>

                <Button
                  variant="outline"
                  onClick={() => setPage(Math.min(pages, page + 1))}
                  disabled={page === pages}
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
