import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import type {
  PaginatedResponse,
  ETTransferDetail,
  Protocol,
  Technician,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { ChevronLeft, ChevronRight, Plus, Search } from "lucide-react";

export default function DataEntryPage() {
  const navigate = useNavigate();
  const [transfers, setTransfers] = useState<ETTransferDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [search, setSearch] = useState("");
  const [filterResult, setFilterResult] = useState("");
  const [filterProtocol, setFilterProtocol] = useState("");
  const [filterTech, setFilterTech] = useState("");
  const [loading, setLoading] = useState(true);
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);

  const pageSize = 25;

  // Load reference data
  useEffect(() => {
    Promise.all([
      api.get<PaginatedResponse<Protocol>>("/protocols/", {
        params: { page_size: 100 },
      }),
      api.get<PaginatedResponse<Technician>>("/technicians/", {
        params: { page_size: 100 },
      }),
    ]).then(([protocolRes, techRes]) => {
      setProtocols(protocolRes.data.items);
      setTechnicians(techRes.data.items);
    });
  }, []);

  // Load transfers
  useEffect(() => {
    setLoading(true);
    const params: Record<string, string | number> = {
      page,
      page_size: pageSize,
    };
    if (search) params.search = search;
    if (filterResult) params.pc1_result = filterResult;
    if (filterProtocol) params.protocol_id = filterProtocol;
    if (filterTech) params.technician_id = filterTech;

    api
      .get<PaginatedResponse<ETTransferDetail>>("/transfers/", { params })
      .then((res) => {
        setTransfers(res.data.items);
        setTotal(res.data.total);
        setPages(res.data.pages);
      })
      .finally(() => setLoading(false));
  }, [page, search, filterResult, filterProtocol, filterTech]);

  const resultBadge = (result: string | null) => {
    if (!result) return <span className="text-muted-foreground">—</span>;
    const variant =
      result === "Pregnant"
        ? "success"
        : result === "Open"
          ? "destructive"
          : "secondary";
    return <Badge variant={variant}>{result}</Badge>;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">ET Transfer Records</h2>
          <p className="text-sm text-muted-foreground">
            {total} total records
          </p>
        </div>
        <Button onClick={() => navigate("/data-entry/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Transfer
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by customer or location..."
                className="pl-8"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <Select
              value={filterResult}
              onChange={(e) => {
                setFilterResult(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Outcomes</option>
              <option value="Pregnant">Pregnant</option>
              <option value="Open">Open</option>
              <option value="Recheck">Recheck</option>
            </Select>
            <Select
              value={filterProtocol}
              onChange={(e) => {
                setFilterProtocol(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Protocols</option>
              {protocols.map((p) => (
                <option key={p.protocol_id} value={p.protocol_id}>
                  {p.name}
                </option>
              ))}
            </Select>
            <Select
              value={filterTech}
              onChange={(e) => {
                setFilterTech(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Technicians</option>
              {technicians.map((t) => (
                <option key={t.technician_id} value={t.technician_id}>
                  {t.name}
                </option>
              ))}
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : transfers.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center text-muted-foreground">
              <p>No transfer records found</p>
              <p className="text-xs mt-1">
                Import data or create a new record
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">#</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Donor</TableHead>
                  <TableHead>Sire</TableHead>
                  <TableHead>Recipient</TableHead>
                  <TableHead>Protocol</TableHead>
                  <TableHead>CL (mm)</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Tech</TableHead>
                  <TableHead>Result</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transfers.map((t) => (
                  <TableRow
                    key={t.transfer_id}
                    className="cursor-pointer"
                    onClick={() =>
                      navigate(`/data-entry/${t.transfer_id}`)
                    }
                  >
                    <TableCell className="font-mono text-xs">
                      {t.et_number ?? t.transfer_id}
                    </TableCell>
                    <TableCell>{t.et_date}</TableCell>
                    <TableCell>
                      {t.donor_tag ?? "—"}
                      {t.donor_breed && (
                        <span className="ml-1 text-xs text-muted-foreground">
                          ({t.donor_breed})
                        </span>
                      )}
                    </TableCell>
                    <TableCell>{t.sire_name ?? "—"}</TableCell>
                    <TableCell>{t.recipient_tag ?? "—"}</TableCell>
                    <TableCell className="max-w-[150px] truncate text-xs">
                      {t.protocol_name ?? "—"}
                    </TableCell>
                    <TableCell>
                      {t.cl_measure_mm != null ? t.cl_measure_mm : "—"}
                    </TableCell>
                    <TableCell>{t.embryo_stage ?? "—"}</TableCell>
                    <TableCell>{t.technician_name ?? "—"}</TableCell>
                    <TableCell>{resultBadge(t.pc1_result)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {pages} ({total} records)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
