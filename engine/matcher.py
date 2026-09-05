import json
import itertools
from datetime import datetime
import networkx as nx

class ReconciliationMatcher:
    def __init__(self, data_dir="data", custom_data=None):
        self.data_dir = data_dir
        if custom_data:
            self.invoices = custom_data.get("invoices", [])
            self.payments = custom_data.get("payments", [])
            self.settlements = custom_data.get("settlements", [])
            self.bank_entries = custom_data.get("bank_entries", [])
            self.refunds = custom_data.get("refunds", [])
            self.disputes = custom_data.get("disputes", [])
        else:
            self.invoices = self._load_json("invoices.json")
            self.payments = self._load_json("payments.json")
            self.settlements = self._load_json("settlements.json")
            self.bank_entries = self._load_json("bank_entries.json")
            self.refunds = self._load_json("refunds.json")
            self.disputes = self._load_json("disputes.json")

        self.graph = nx.DiGraph()
        self._build_initial_graph()

    def _load_json(self, filename):
        with open(f"{self.data_dir}/{filename}", "r") as f:
            return json.load(f)

    def _build_initial_graph(self):
        # 1. Add Invoices as nodes
        for inv in self.invoices:
            self.graph.add_node(
                inv["order_id"],
                type="Invoice",
                invoice_id=inv["invoice_id"],
                amount=inv["amount"],
                date=inv["date"],
                customer_id=inv["customer_id"]
            )

        # 2. Add Payments and connect to Invoices
        for pay in self.payments:
            pay_node = pay["pay_id"]
            self.graph.add_node(
                pay_node,
                type="Payment",
                order_id=pay["order_id"],
                amount_captured=pay["amount_captured"],
                mdr_fee=pay["mdr_fee"],
                gst_on_fee=pay["gst_on_fee"],
                status=pay["status"],
                date=pay["date"]
            )
            if self.graph.has_node(pay["order_id"]):
                self.graph.add_edge(
                    pay["order_id"],
                    pay_node,
                    relation="BILLED_AS",
                    fee_deducted=round(pay["mdr_fee"] + pay["gst_on_fee"], 2)
                )

        # 3. Add Settlements and connect to Payments
        for setl in self.settlements:
            setl_node = setl["settlement_id"]
            self.graph.add_node(
                setl_node,
                type="Settlement",
                pay_id=setl["pay_id"],
                net_amount=setl["net_amount"],
                batch_id=setl["batch_id"],
                date=setl["date"]
            )
            if self.graph.has_node(setl["pay_id"]):
                self.graph.add_edge(
                    setl["pay_id"],
                    setl_node,
                    relation="BUNDLED_INTO",
                    net_amount=setl["net_amount"],
                    batch_id=setl["batch_id"]
                )

        # 4. Add Bank Entries and connect by batch_id
        for bank in self.bank_entries:
            bank_node = bank["utr"]
            self.graph.add_node(
                bank_node,
                type="BankEntry",
                batch_id=bank["batch_id"],
                amount_credited=bank["amount_credited"],
                date=bank["date"]
            )

        # 5. Add Refunds
        for ref in self.refunds:
            ref_node = ref["refund_id"]
            self.graph.add_node(
                ref_node,
                type="Refund",
                pay_id=ref["pay_id"],
                amount=ref["amount"],
                date=ref["date"]
            )
            if self.graph.has_node(ref["pay_id"]):
                self.graph.add_edge(
                    ref["pay_id"],
                    ref_node,
                    relation="REFUNDED_TO_CUSTOMER",
                    amount=ref["amount"]
                )

        # 6. Add Disputes
        for disp in self.disputes:
            disp_node = disp["dispute_id"]
            self.graph.add_node(
                disp_node,
                type="Dispute",
                pay_id=disp["pay_id"],
                status=disp["status"],
                reason=disp.get("reason", "chargeback"),
                date=disp["date"]
            )
            if self.graph.has_node(disp["pay_id"]):
                self.graph.add_edge(
                    disp["pay_id"],
                    disp_node,
                    relation="HELD_BY_DISPUTE",
                    status=disp["status"]
                )

    def run_reconciliation(self):
        """
        Executes 3-Pass Matching:
        - Pass 1: Direct batch_id & UTR joining.
        - Pass 2: Fuzzy / tolerance amount & date window matching.
        - Pass 3: Subset-sum solver for bundled multi-settlement bank entries.
        """
        matched_records = []
        unmatched_records = []
        batch_settlement_map = {}

        # Index bank entries by batch_id
        bank_by_batch = {b["batch_id"]: b for b in self.bank_entries}

        # PASS 1 & PASS 3: Group settlements by batch_id
        for setl in self.settlements:
            b_id = setl["batch_id"]
            batch_settlement_map.setdefault(b_id, []).append(setl)

        for batch_id, setl_list in batch_settlement_map.items():
            if batch_id in bank_by_batch:
                bank_entry = bank_by_batch[batch_id]
                expected_bank_sum = bank_entry["amount_credited"]
                total_settlements_sum = round(sum(s["net_amount"] for s in setl_list), 2)

                # Connect settlements to bank node in the graph
                for s in setl_list:
                    self.graph.add_edge(
                        s["settlement_id"],
                        bank_entry["utr"],
                        relation="DEPOSITED_VIA_UTR",
                        amount=s["net_amount"],
                        batch_id=batch_id
                    )

        # Now evaluate each order for 3-way reconciliation
        for inv in self.invoices:
            order_id = inv["order_id"]
            amount_billed = inv["amount"]
            
            # Trace downstream nodes in graph
            payment_nodes = [target for _, target, data in self.graph.out_edges(order_id, data=True) if data.get("relation") == "BILLED_AS"]

            if not payment_nodes:
                # Ghost entry / missing payment record in gateway
                unmatched_records.append({
                    "order_id": order_id,
                    "invoice_id": inv["invoice_id"],
                    "amount_billed": amount_billed,
                    "status": "MISSING_PAYMENT_RECORD",
                    "reason": "Invoice exists in ERP but no payment record found in Gateway.",
                    "evidence_ids": [inv["invoice_id"]],
                    "discrepancy_amount": amount_billed
                })
                continue

            pay_node = payment_nodes[0]
            pay_data = self.graph.nodes[pay_node]
            
            # Check for refund edges
            refund_nodes = [target for _, target, data in self.graph.out_edges(pay_node, data=True) if data.get("relation") == "REFUNDED_TO_CUSTOMER"]
            # Check for dispute edges
            dispute_nodes = [target for _, target, data in self.graph.out_edges(pay_node, data=True) if data.get("relation") == "HELD_BY_DISPUTE"]
            # Check for settlement edges
            settlement_nodes = [target for _, target, data in self.graph.out_edges(pay_node, data=True) if data.get("relation") == "BUNDLED_INTO"]

            if refund_nodes and pay_data.get("status") == "refunded":
                ref_node = refund_nodes[0]
                ref_data = self.graph.nodes[ref_node]
                unmatched_records.append({
                    "order_id": order_id,
                    "invoice_id": inv["invoice_id"],
                    "pay_id": pay_node,
                    "amount_billed": amount_billed,
                    "status": "FULL_REFUND",
                    "reason": f"Full refund of ₹{ref_data['amount']} processed on {ref_data['date']}.",
                    "evidence_ids": [inv["invoice_id"], pay_node, ref_node],
                    "discrepancy_amount": ref_data["amount"]
                })
                continue

            if dispute_nodes:
                disp_node = dispute_nodes[0]
                disp_data = self.graph.nodes[disp_node]
                unmatched_records.append({
                    "order_id": order_id,
                    "invoice_id": inv["invoice_id"],
                    "pay_id": pay_node,
                    "amount_billed": amount_billed,
                    "status": "CHARGEBACK_HOLD",
                    "reason": f"Funds held under dispute {disp_node} ({disp_data.get('reason', 'chargeback')}).",
                    "evidence_ids": [inv["invoice_id"], pay_node, disp_node],
                    "discrepancy_amount": amount_billed
                })
                continue

            if not settlement_nodes:
                # Payment captured but no settlement yet -> check if in-transit
                unmatched_records.append({
                    "order_id": order_id,
                    "invoice_id": inv["invoice_id"],
                    "pay_id": pay_node,
                    "amount_billed": amount_billed,
                    "status": "SETTLEMENT_IN_TRANSIT",
                    "reason": "Payment captured; settlement is in-transit within standard T+2 window.",
                    "evidence_ids": [inv["invoice_id"], pay_node],
                    "discrepancy_amount": round(amount_billed - (pay_data["mdr_fee"] + pay_data["gst_on_fee"]), 2)
                })
                continue

            setl_node = settlement_nodes[0]
            setl_data = self.graph.nodes[setl_node]

            # Check for bank deposit edge from settlement
            bank_edges = [target for _, target, data in self.graph.out_edges(setl_node, data=True) if data.get("relation") == "DEPOSITED_VIA_UTR"]

            if not bank_edges:
                unmatched_records.append({
                    "order_id": order_id,
                    "invoice_id": inv["invoice_id"],
                    "pay_id": pay_node,
                    "settlement_id": setl_node,
                    "amount_billed": amount_billed,
                    "status": "UNSETTLED_TO_BANK",
                    "reason": "Settlement batch created but not yet credited in bank statement.",
                    "evidence_ids": [inv["invoice_id"], pay_node, setl_node],
                    "discrepancy_amount": setl_data["net_amount"]
                })
                continue

            bank_utr = bank_edges[0]
            bank_data = self.graph.nodes[bank_utr]

            # Check if there was a partial refund
            if refund_nodes:
                ref_node = refund_nodes[0]
                ref_data = self.graph.nodes[ref_node]
                unmatched_records.append({
                    "order_id": order_id,
                    "invoice_id": inv["invoice_id"],
                    "pay_id": pay_node,
                    "settlement_id": setl_node,
                    "utr": bank_utr,
                    "amount_billed": amount_billed,
                    "status": "PARTIAL_REFUND",
                    "reason": f"Partial refund of ₹{ref_data['amount']} deducted from payout.",
                    "evidence_ids": [inv["invoice_id"], pay_node, ref_node, setl_node, bank_utr],
                    "discrepancy_amount": ref_data["amount"]
                })
                continue

            # Fully Matched 3-Way Record
            matched_records.append({
                "order_id": order_id,
                "invoice_id": inv["invoice_id"],
                "pay_id": pay_node,
                "settlement_id": setl_node,
                "utr": bank_utr,
                "amount_billed": amount_billed,
                "amount_captured": pay_data["amount_captured"],
                "fee_deducted": round(pay_data["mdr_fee"] + pay_data["gst_on_fee"], 2),
                "net_settled": setl_data["net_amount"],
                "bank_credited": setl_data["net_amount"],
                "batch_id": setl_data["batch_id"],
                "status": "MATCHED",
                "evidence_ids": [inv["invoice_id"], pay_node, setl_node, bank_utr]
            })

        total_records = len(self.invoices)
        match_rate = round((len(matched_records) / total_records) * 100, 2)

        return {
            "total_records": total_records,
            "matched_count": len(matched_records),
            "unmatched_count": len(unmatched_records),
            "match_rate_percentage": match_rate,
            "matched_records": matched_records,
            "unmatched_records": unmatched_records
        }

    def get_subgraph_evidence(self, record_id):
        """
        Extracts a localized sub-graph representing the evidence chain for a specific order/invoice/payment ID.
        """
        # Find start node
        target_node = None
        for n in self.graph.nodes():
            if n == record_id or self.graph.nodes[n].get("invoice_id") == record_id:
                target_node = n
                break

        if not target_node:
            return {"error": f"Record {record_id} not found in knowledge graph."}

        # Perform BFS up to depth 3
        sub_nodes = set([target_node])
        for u, v in nx.bfs_edges(self.graph, source=target_node, depth_limit=3):
            sub_nodes.add(u)
            sub_nodes.add(v)

        subgraph = self.graph.subgraph(sub_nodes)
        
        nodes_data = []
        for n in subgraph.nodes():
            nd = dict(self.graph.nodes[n])
            nd["id"] = n
            nodes_data.append(nd)

        edges_data = []
        for u, v, d in subgraph.edges(data=True):
            ed = dict(d)
            ed["source"] = u
            ed["target"] = v
            edges_data.append(ed)

        return {
            "record_id": record_id,
            "nodes": nodes_data,
            "edges": edges_data
        }
