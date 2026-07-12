using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private const int TableDirectoryPageSize = 100;

    private async Task<ApiResponseEnvelope<List<RunTableDirectoryItemDto>>> LoadRunTableDirectoryAsync(
        string workflowRunId,
        CancellationToken cancellationToken)
    {
        var result = new List<RunTableDirectoryItemDto>();
        var offset = 0;
        while (true)
        {
            var response = await runMetadataCache.GetTableRefsAsync(
                BuildSettings(),
                workflowRunId,
                offset,
                TableDirectoryPageSize,
                cancellationToken: cancellationToken);
            if (!response.Ok || response.Data is null)
            {
                return new ApiResponseEnvelope<List<RunTableDirectoryItemDto>>
                {
                    Ok = false,
                    Error = response.Error,
                    RequestId = response.RequestId,
                };
            }

            var page = response.Data;
            result.AddRange(page.Items);
            if (!page.HasMore)
            {
                return ApiResponseEnvelope<List<RunTableDirectoryItemDto>>.Success(
                    result,
                    response.RequestId);
            }

            var nextOffset = page.Offset + page.Items.Length;
            if (nextOffset <= offset)
            {
                nextOffset = offset + System.Math.Max(1, page.Limit);
            }

            offset = nextOffset;
        }
    }
}
