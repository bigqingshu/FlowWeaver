using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class RunReviewService : IRunReviewService
{
    private readonly IEngineHostApiClient apiClient;

    public RunReviewService(IEngineHostApiClient apiClient)
    {
        this.apiClient = apiClient;
    }

    public Task<ApiResponseEnvelope<RunReviewDto>> GetAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return apiClient.GetRunReviewAsync(
            settings,
            workflowRunId,
            cancellationToken);
    }
}
