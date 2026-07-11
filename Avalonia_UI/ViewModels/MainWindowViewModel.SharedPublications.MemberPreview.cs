using System;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private CancellationTokenSource? sharedPublicationMemberPreviewCancellation;

    private int sharedPublicationMemberPreviewVersion;

    private bool isSharedPublicationMemberPreviewActive;

    private async Task PreviewSharedPublicationMemberAsync(
        SharedPublicationMemberListItemViewModel member)
    {
        SelectedSharedPublicationVersionMember = member;
        if (!member.CanReadRows)
        {
            SharedPublicationVersionErrorMessage = member.AvailabilityText;
            return;
        }

        CancelSharedPublicationMemberPreviewRequest();
        ClearActiveSharedPublicationMemberPreview();
        var request = CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        var cancellationToken = request.Token;
        sharedPublicationMemberPreviewCancellation = request;
        var requestVersion = ++sharedPublicationMemberPreviewVersion;
        try
        {
            var response = await _apiClient.GetTableRefAsync(
                BuildSettings(),
                member.TableRefId,
                cancellationToken);
            if (requestVersion != sharedPublicationMemberPreviewVersion
                || SelectedSharedPublicationVersionMember?.TableRefId
                != member.TableRefId)
            {
                return;
            }

            if (!response.Ok || response.Data is null)
            {
                var error = DescribeSharedPublicationMemberPreviewError(response.Error);
                SharedPublicationVersionErrorMessage = error;
                DataPreviewWorkbenchMessage = T("data_preview.workbench_load_failed");
                DataPreviewWorkbenchErrorMessage = error;
                return;
            }

            if (!response.Data.CanReadRows)
            {
                var error = T("data.shared_member.unavailable");
                SharedPublicationVersionErrorMessage = error;
                DataPreviewWorkbenchMessage = T("data_preview.workbench_load_failed");
                DataPreviewWorkbenchErrorMessage = error;
                return;
            }

            var tableRef = new TableRefListItemViewModel(response.Data, T);
            isSharedPublicationMemberPreviewActive = true;
            SelectedDataPreviewState = null;
            SelectedDataPreviewTableOption = tableRef;
            SelectedDataPreviewTableRef = tableRef;
            SharedPublicationVersionErrorMessage = null;
            SelectedShellPageKey = ShellPageKey.DataPreview;
            await LoadDataPreviewWorkbenchTablePageAsync(tableRef, offset: 0);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        finally
        {
            if (ReferenceEquals(sharedPublicationMemberPreviewCancellation, request))
            {
                sharedPublicationMemberPreviewCancellation = null;
            }

            request.Dispose();
        }
    }

    private string DescribeSharedPublicationMemberPreviewError(ApiErrorDto? error)
    {
        return error?.ErrorCode is "TABLE_REF_NOT_AVAILABLE" or "TABLE_REF_NOT_FOUND"
            ? T("data.shared_member.unavailable")
            : error?.Message ?? T("data.shared_member.unavailable");
    }

    private void ResetSharedPublicationMemberPreviewState()
    {
        CancelSharedPublicationMemberPreviewRequest();
        ClearActiveSharedPublicationMemberPreview();
        SelectedSharedPublicationVersionMember = null;
    }

    private void CancelSharedPublicationMemberPreviewRequest()
    {
        sharedPublicationMemberPreviewVersion++;
        sharedPublicationMemberPreviewCancellation?.Cancel();
        sharedPublicationMemberPreviewCancellation?.Dispose();
        sharedPublicationMemberPreviewCancellation = null;
    }

    private void ClearActiveSharedPublicationMemberPreview()
    {
        if (!isSharedPublicationMemberPreviewActive)
        {
            return;
        }

        CancelDataPreviewWorkbenchLoadForSelectionChange();
        ResetDataPreviewWorkbenchState();
        isSharedPublicationMemberPreviewActive = false;
    }
}
