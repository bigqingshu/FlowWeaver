using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;

namespace Avalonia_UI.Services;

public interface ISharedPublicationCatalogService
{
    Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>> SearchSharesAsync(
        string? query,
        int offset,
        int limit,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>> ListVersionsAsync(
        string shareName,
        int offset,
        int limit,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>> ListMembersAsync(
        string publicationId,
        int offset,
        int limit,
        CancellationToken cancellationToken = default);
}
