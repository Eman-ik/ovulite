"""
Integration tests for Analytics API endpoints.

Tests:
- CT-19: GET /analytics/kpis returns KPIs (pregnancy rate, conception rate, etc.)
- CT-20: GET /analytics/trends returns monthly trends
- CT-21: GET /analytics/funnel returns IVF funnel stages
- CT-22: GET /analytics/protocols returns protocol performance
- Additional: donors, biomarkers, breeds endpoints
"""
import pytest


@pytest.mark.integration
class TestAnalyticsKPIEndpoint:
    """Test core KPI endpoint - CT-19"""

    def test_analytics_kpis_returns_200(self, client, auth_headers):
        """CT-19: Test that GET /analytics/kpis returns core KPIs"""
        response = client.get(
            "/analytics/kpis",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have core KPI fields
        assert isinstance(data, dict)
        # Expected KPIs based on schema
        kpi_fields = [
            "pregnancy_rate", "conception_rate", "total_transfers", 
            "total_pregnancies", "avg_cl_measure", "avg_embryo_grade"
        ]
        # At least some of these should be present
        has_kpis = any(field in data for field in kpi_fields)
        assert has_kpis, f"KPI response should contain at least one of: {kpi_fields}"

    def test_kpis_have_numeric_values(self, client, auth_headers):
        """Test that KPIs are numeric values"""
        response = client.get(
            "/analytics/kpis",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Most KPI values should be numeric
        numeric_fields = [v for v in data.values() if isinstance(v, (int, float))]
        assert len(numeric_fields) > 0, "KPIs should contain numeric values"

    def test_pregnancy_rate_in_valid_range(self, client, auth_headers):
        """Test that pregnancy rate (if present) is between 0 and 100"""
        response = client.get(
            "/analytics/kpis",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "pregnancy_rate" in data:
            rate = data["pregnancy_rate"]
            assert 0.0 <= rate <= 100.0, f"Pregnancy rate {rate} out of valid range [0, 100]"


@pytest.mark.integration
class TestAnalyticsTrendsEndpoint:
    """Test monthly trends endpoint - CT-20"""

    def test_analytics_trends_returns_200(self, client, auth_headers):
        """CT-20: Test that GET /analytics/trends returns monthly trends"""
        response = client.get(
            "/analytics/trends",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of monthly trend objects
        assert isinstance(data, list)

    def test_trends_have_required_fields(self, client, auth_headers):
        """Test that trend objects have month and metric fields"""
        response = client.get(
            "/analytics/trends",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If there are trends, check structure
        if len(data) > 0:
            trend = data[0]
            assert "month" in trend or "date" in trend or "period" in trend
            # Should have some metric values
            has_metrics = any(
                k in trend 
                for k in ["pregnancy_rate", "transfer_count", "value"]
            )
            assert has_metrics, "Trend should contain metric values"

    def test_trends_chronological_order(self, client, auth_headers):
        """Test that trends are in chronological order"""
        response = client.get(
            "/analytics/trends",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If there are multiple trends, check ordering
        if len(data) >= 2:
            # Should have month/date field
            date_field = None
            for field in ["month", "date", "period"]:
                if field in data[0]:
                    date_field = field
                    break
            
            if date_field:
                dates = [t[date_field] for t in data]
                # Should be sorted (either ascending or descending)
                assert dates == sorted(dates) or dates == sorted(dates, reverse=True)


@pytest.mark.integration
class TestAnalyticsFunnelEndpoint:
    """Test IVF funnel endpoint - CT-21"""

    def test_analytics_funnel_returns_200(self, client, auth_headers):
        """CT-21: Test that GET /analytics/funnel returns IVF funnel stages"""
        response = client.get(
            "/analytics/funnel",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have stages list
        assert "stages" in data
        assert isinstance(data["stages"], list)

    def test_funnel_stages_structure(self, client, auth_headers):
        """Test that funnel stages have required fields"""
        response = client.get(
            "/analytics/funnel",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        stages = data["stages"]
        # If there are stages, check structure
        if len(stages) > 0:
            stage = stages[0]
            assert "stage" in stage or "name" in stage
            assert "count" in stage or "value" in stage
            # May have conversion rate
            if "conversion_rate" in stage:
                assert 0.0 <= stage["conversion_rate"] <= 100.0

    def test_funnel_stages_descending_counts(self, client, auth_headers):
        """Test that funnel stages show descending counts (funnel shape)"""
        response = client.get(
            "/analytics/funnel",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        stages = data["stages"]
        # Funnel should generally show decreasing counts
        if len(stages) >= 2:
            count_field = "count" if "count" in stages[0] else "value"
            if count_field in stages[0]:
                counts = [s[count_field] for s in stages]
                # Generally each stage should have fewer than previous
                # (allows some flexibility for data variations)
                assert counts[0] >= counts[-1], "Funnel should taper down"


@pytest.mark.integration
class TestAnalyticsProtocolsEndpoint:
    """Test protocol performance endpoint - CT-22"""

    def test_analytics_protocols_returns_200(self, client, auth_headers):
        """CT-22: Test that GET /analytics/protocols returns protocol performance"""
        response = client.get(
            "/analytics/protocols",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have protocols list
        assert "protocols" in data
        assert isinstance(data["protocols"], list)

    def test_protocol_stats_structure(self, client, auth_headers):
        """Test that protocol stats have required fields"""
        response = client.get(
            "/analytics/protocols",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        protocols = data["protocols"]
        # If there are protocols, check structure
        if len(protocols) > 0:
            protocol = protocols[0]
            assert "protocol_name" in protocol
            assert "pregnancy_rate" in protocol
            assert "n_transfers" in protocol


@pytest.mark.integration
class TestAnalyticsDonorsEndpoint:
    """Test donor performance endpoint"""

    def test_analytics_donors_returns_200(self, client, auth_headers):
        """Test that GET /analytics/donors returns donor performance"""
        response = client.get(
            "/analytics/donors",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have donors list
        assert "donors" in data
        assert isinstance(data["donors"], list)

    def test_donor_stats_structure(self, client, auth_headers):
        """Test that donor stats have required fields"""
        response = client.get(
            "/analytics/donors",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        donors = data["donors"]
        if len(donors) > 0:
            donor = donors[0]
            assert "donor_tag" in donor
            # Should have performance metrics
            has_metrics = any(
                k in donor 
                for k in ["pregnancy_rate", "n_transfers", "avg_cl"]
            )
            assert has_metrics


@pytest.mark.integration
class TestAnalyticsBiomarkersEndpoint:
    """Test biomarker analysis endpoint"""

    def test_analytics_biomarkers_returns_200(self, client, auth_headers):
        """Test that GET /analytics/biomarkers returns biomarker analysis"""
        response = client.get(
            "/analytics/biomarkers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have biomarker fields (cl_measure, bc_score, heat_day)
        biomarker_fields = ["cl_measure", "bc_score", "heat_day"]
        has_biomarkers = any(field in data for field in biomarker_fields)
        assert has_biomarkers, f"Response should contain at least one biomarker field: {biomarker_fields}"

    def test_biomarker_results_structure(self, client, auth_headers):
        """Test that biomarker results have required fields"""
        response = client.get(
            "/analytics/biomarkers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure - biomarkers are direct keys (cl_measure, bc_score, heat_day)
        biomarker_fields = ["cl_measure", "bc_score", "heat_day"]
        available_biomarkers = [field for field in biomarker_fields if field in data and data[field] is not None]
        
        if len(available_biomarkers) > 0:
            result = data[available_biomarkers[0]]
            # Should have bins and biomarker statistics
            assert "bins" in result
            assert isinstance(result["bins"], list)


@pytest.mark.integration
class TestAnalyticsPipelineEndpoint:
    """Test analytics pipeline trigger"""

    def test_analytics_run_triggers_pipeline(self, client, auth_headers):
        """Test that POST /analytics/run triggers analytics pipeline"""
        response = client.post(
            "/analytics/run",
            headers=auth_headers
        )
        
        # Should return 200 or 202
        assert response.status_code in [200, 202]
        data = response.json()
        
        # Should have status message
        assert "status" in data or "message" in data


@pytest.mark.integration
class TestAnalyticsAuthEnforcement:
    """Ensure analytics endpoints are protected by authentication."""

    @pytest.mark.parametrize(
        "endpoint,method",
        [
            ("/analytics/kpis", "get"),
            ("/analytics/trends", "get"),
            ("/analytics/funnel", "get"),
            ("/analytics/protocols", "get"),
            ("/analytics/donors", "get"),
            ("/analytics/breeds", "get"),
            ("/analytics/biomarkers", "get"),
            ("/analytics/run", "post"),
        ],
    )
    def test_analytics_endpoint_requires_auth(self, client, endpoint, method):
        response = getattr(client, method)(endpoint)
        assert response.status_code == 401, f"Expected 401 for {method.upper()} {endpoint}"
