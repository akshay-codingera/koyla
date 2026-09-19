// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { TopicIntelligence } from '../pages/TopicIntelligence';
import { apiClient } from '../api/client';

vi.mock('../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('TopicIntelligence Component (Phase 8.4)', () => {
  const mockAnalysisId = 'test-analysis-uuid-1234';

  const mockAnalysisMeta = {
    id: mockAnalysisId,
    organization_id: 'org-ecl-uuid',
    organization_code: 'ECL',
    organization_name: 'Eastern Coalfields Limited',
    corpus_filters: { organization_id: 'org-ecl-uuid' },
    corpus_hash: 'abc123456789hash',
    embedding_model: 'BAAI/bge-small-en-v1.5',
    analysis_method: 'EMBEDDING_CLUSTER_CTFIDF',
    status: 'COMPLETED',
    progress_pct: 100,
    runtime_seconds: 4.25,
    document_count: 20,
    chunk_count: 48,
    topic_count: 3,
    outlier_count: 2,
    quality_metrics: {
      semantic_topic_coherence: 0.742,
      topic_diversity: 0.88,
    },
    created_at: '2026-09-19T10:00:00Z',
  };

  const mockTopics = [
    {
      id: 'topic-1-uuid',
      analysis_id: mockAnalysisId,
      topic_index: 0,
      label: 'Groundwater & Drainage (Seam, Water)',
      document_count: 8,
      chunk_count: 18,
      prevalence_pct: 40.0,
      semantic_topic_coherence: 0.765,
      top_terms: [
        { term: 'groundwater', weight: 0.1425, rank: 1, frequency: 24, document_count: 8 },
        { term: 'drainage', weight: 0.1120, rank: 2, frequency: 18, document_count: 7 },
        { term: 'aquifer', weight: 0.0890, rank: 3, frequency: 12, document_count: 5 },
      ],
    },
    {
      id: 'topic-2-uuid',
      analysis_id: mockAnalysisId,
      topic_index: 1,
      label: 'Afforestation & Biological Reclamation',
      document_count: 6,
      chunk_count: 14,
      prevalence_pct: 30.0,
      semantic_topic_coherence: 0.712,
      top_terms: [
        { term: 'afforestation', weight: 0.1310, rank: 1, frequency: 16, document_count: 6 },
        { term: 'reclamation', weight: 0.1050, rank: 2, frequency: 14, document_count: 5 },
      ],
    },
  ];

  const mockTrends = [
    {
      topic_id: 'topic-1-uuid',
      label: 'Groundwater & Drainage (Seam, Water)',
      first_seen: 'FY2023-24',
      last_seen: 'FY2025-26',
      observed_periods: 3,
      total_periods: 3,
      persistence_status: 'PERSISTENT',
      series: [
        {
          period_value: 'FY2023-24',
          document_count: 2,
          corpus_document_count: 6,
          document_share_pct: 33.33,
          chunk_count: 5,
          corpus_chunk_count: 15,
          chunk_share_pct: 33.33,
          absolute_change: null,
          percentage_point_change: null,
          growth_rate_pct: null,
          trend_status: 'INSUFFICIENT_HISTORY',
        },
        {
          period_value: 'FY2024-25',
          document_count: 3,
          corpus_document_count: 7,
          document_share_pct: 42.86,
          chunk_count: 6,
          corpus_chunk_count: 16,
          chunk_share_pct: 37.5,
          absolute_change: 1,
          percentage_point_change: 9.53,
          growth_rate_pct: 28.59,
          trend_status: 'GROWING',
        },
      ],
    },
  ];

  const mockEvidence = [
    {
      evidence_id: 'ev-1',
      chunk_id: 'chk-1-uuid-1234',
      document_id: 'doc-1-uuid-5678',
      document_title: 'Rajmahal OCP Hydrogeological Evaluation',
      document_type: 'GEOLOGICAL_REPORT',
      organization_code: 'ECL',
      page_number: 17,
      section_heading: 'Chapter 2: Water Regime',
      content: 'Groundwater inflow in Simlong block exceeds 250 cubic meters per hour.',
      representative_score: 0.895,
      mine_name: 'Rajmahal OCP',
      block_name: 'Simlong Block',
      fiscal_year: 'FY2024-25',
    },
  ];

  const setupDefaultMocks = () => {
    (apiClient.get as any).mockImplementation((url: string, config?: any) => {
      if (url === '/topics?limit=30') {
        return Promise.resolve({ data: { total: 1, items: [mockAnalysisMeta] } });
      }
      if (url === `/topics/${mockAnalysisId}` || url.startsWith(`/topics/${mockAnalysisId}?`)) {
        return Promise.resolve({ data: mockAnalysisMeta });
      }
      if (url === `/topics/${mockAnalysisId}/topics`) {
        return Promise.resolve({ data: { topics: mockTopics } });
      }
      if (url === `/topics/${mockAnalysisId}/trends`) {
        return Promise.resolve({ data: { periods: ['FY2023-24', 'FY2024-25'], trends: mockTrends } });
      }
      if (url === `/topics/${mockAnalysisId}/topics/topic-1-uuid`) {
        return Promise.resolve({
          data: {
            ...mockTopics[0],
            terms: mockTopics[0].top_terms,
            documents: [{ document_title: 'Rajmahal OCP Hydrogeological Evaluation', contribution_pct: 45.0 }],
          },
        });
      }
      if (url === `/topics/${mockAnalysisId}/topics/topic-1-uuid/evidence?limit=15`) {
        return Promise.resolve({ data: { items: mockEvidence } });
      }
      if (url.includes('/term-evolution')) {
        return Promise.resolve({
          data: {
            topic_id: 'topic-1-uuid',
            topic_label: 'Groundwater & Drainage',
            periods: ['FY2023-24', 'FY2024-25'],
            term_evolution: [
              { term: 'groundwater', global_rank: 1, global_weight: 0.1425, period_frequencies: { 'FY2023-24': 10, 'FY2024-25': 14 } },
            ],
          },
        });
      }
      if (url.includes('/comparison')) {
        return Promise.resolve({
          data: {
            analysis_id: mockAnalysisId,
            period_a: 'FY2023-24',
            period_b: 'FY2024-25',
            comparisons: [
              {
                topic_id: 'topic-1-uuid',
                topic_label: 'Groundwater & Drainage',
                document_share_a_pct: 33.33,
                document_share_b_pct: 42.86,
                percentage_point_change: 9.53,
                absolute_change: 1,
                document_count_a: 2,
                document_count_b: 3,
                corpus_document_count_a: 6,
                corpus_document_count_b: 7,
                trend_status: 'GROWING',
              },
            ],
          },
        });
      }
      if (url === '/reports') {
        return Promise.resolve({
          data: [
            { id: 'rep-uuid-1', report_title: 'Mining Plan Rajmahal OCP 2026', status: 'DRAFT' },
          ],
        });
      }
      return Promise.resolve({ data: {} });
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
    window.history.pushState({}, '', '/');
    setupDefaultMocks();
  });

  it('1. Renders Topic Intelligence header, analysis metadata, and control bar', async () => {
    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/TOPIC INTELLIGENCE CONTROL ROOM/i)).toBeDefined();
      expect(screen.getByText(/BAAI\/bge-small-en-v1.5/i)).toBeDefined();
      expect(screen.getByText(/20 Docs · 48 Chunks/i)).toBeDefined();
    });
  });

  it('2. Renders Topic Register table with real API data and trend badges', async () => {
    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/Groundwater & Drainage/i).length).toBeGreaterThan(0);
      expect(screen.getByText('40.0%')).toBeDefined();
      expect(screen.getByText(/Afforestation & Biological/i)).toBeDefined();
      expect(screen.getByText('30.0%')).toBeDefined();
    });
  });

  it('3. Navigates to Word Cloud tab and displays term weights', async () => {
    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/Groundwater & Drainage/i).length).toBeGreaterThan(0);
    });

    const wordCloudTab = screen.getAllByRole('button', { name: /WORD CLOUD/i })[0];
    fireEvent.click(wordCloudTab);

    await waitFor(() => {
      expect(screen.getByText(/MATHEMATICAL CLASS-BASED TF-IDF WORD CLOUD/i)).toBeDefined();
      expect(screen.getAllByText('groundwater').length).toBeGreaterThan(0);
      expect(screen.getAllByText('afforestation').length).toBeGreaterThan(0);
    });
  });

  it('4. Navigates to Temporal Trends and displays period prevalence points with sample size', async () => {
    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/Groundwater & Drainage/i).length).toBeGreaterThan(0);
    });

    const trendsTab = screen.getAllByRole('button', { name: /TEMPORAL TRENDS/i })[0];
    fireEvent.click(trendsTab);

    await waitFor(() => {
      expect(screen.getByText(/TOPIC PREVALENCE OVER TIME/i)).toBeDefined();
      expect(screen.getAllByText('33.3%').length).toBeGreaterThan(0);
      expect(screen.getAllByText('42.9%').length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Sample:/i).length).toBeGreaterThan(0);
    });
  });

  it('5. Navigates to Year-to-Year shift and displays percentage point movement', async () => {
    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/Groundwater & Drainage/i).length).toBeGreaterThan(0);
    });

    const yoyTab = screen.getAllByRole('button', { name: /YEAR-TO-YEAR SHIFT/i })[0];
    fireEvent.click(yoyTab);

    await waitFor(() => {
      expect(screen.getByText(/YEAR-TO-YEAR TOPIC SHIFT & PROGRESSION/i)).toBeDefined();
      expect(screen.getAllByText('+9.53 pp').length).toBeGreaterThan(0);
      expect(screen.getAllByText('+1 docs').length).toBeGreaterThan(0);
    });
  });

  it('6. Navigates to Topic Detail and renders grounded evidence cards with VIEW SOURCE', async () => {
    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/Groundwater & Drainage/i).length).toBeGreaterThan(0);
    });

    const detailTab = screen.getAllByRole('button', { name: /TOPIC DETAIL & EVIDENCE/i })[0];
    fireEvent.click(detailTab);

    await waitFor(() => {
      expect(screen.getByText(/SELECTED TOPIC DOSSIER/i)).toBeDefined();
      expect(screen.getByText(/GROUNDED EVIDENCE CARDS & PHYSICAL PROVENANCE/i)).toBeDefined();
      expect(screen.getAllByText(/Page 17/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/VIEW SOURCE/i).length).toBeGreaterThan(0);
    });
  });

  it('7. Displays deterministic refusal alert when corpus is insufficient', async () => {
    window.history.pushState({}, '', '/?id=insufficient-analysis-uuid');
    (apiClient.get as any).mockImplementation((url: string) => {
      if (url === '/topics?limit=30') {
        return Promise.resolve({
          data: {
            total: 1,
            items: [
              {
                id: 'insufficient-analysis-uuid',
                status: 'INSUFFICIENT_CORPUS',
                document_count: 1,
                chunk_count: 1,
                minimum_threshold: { documents: 2, chunks: 3 },
                message: 'INSUFFICIENT CORPUS FOR TOPIC MODELING',
              },
            ],
          },
        });
      }
      if (url === '/topics/insufficient-analysis-uuid' || url.startsWith('/topics/insufficient-analysis-uuid?')) {
        return Promise.resolve({
          data: {
            id: 'insufficient-analysis-uuid',
            status: 'INSUFFICIENT_CORPUS',
            document_count: 1,
            chunk_count: 1,
            minimum_threshold: { documents: 2, chunks: 3 },
            message: 'INSUFFICIENT CORPUS FOR TOPIC MODELING',
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/INSUFFICIENT CORPUS FOR TOPIC MODELING/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Observed Documents:/i)).toBeDefined();
      expect(screen.getByText(/Deterministic Refusal Applied/i)).toBeDefined();
    });

    setupDefaultMocks();
  });

  it('8. Opens Add to Report modal and triggers optional annexure attachment', async () => {
    (apiClient.post as any).mockResolvedValue({
      data: {
        message: 'Topic analysis attached as an optional analytical annexure to statutory report.',
        report_id: 'rep-uuid-1',
      },
    });

    render(
      <BrowserRouter>
        <TopicIntelligence />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/Groundwater & Drainage/i).length).toBeGreaterThan(0);
    });

    const addBtns = screen.getAllByRole('button', { name: /Add Analysis to Report/i });
    fireEvent.click(addBtns[0]);

    await waitFor(() => {
      expect(screen.getByText(/ADD ANALYSIS TO STATUTORY REPORT/i)).toBeDefined();
    });

    const confirmBtn = screen.getByRole('button', { name: /Confirm & Attach to Report/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        `/topics/${mockAnalysisId}/add-to-report`,
        expect.objectContaining({
          report_id: 'rep-uuid-1',
          include_trends: true,
          include_evidence: true,
        })
      );
    });
  });
});
