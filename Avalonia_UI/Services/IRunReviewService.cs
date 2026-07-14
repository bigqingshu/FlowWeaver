using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public interface IRunReviewService
{
    Task<ApiResponseEnvelope<RunReviewDto>> GetAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);
}
