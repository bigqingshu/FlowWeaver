using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanRefreshSharedPublicationCleanupPreview()
    {
        return CanUseEngineActions
            && SelectedSharedPublicationVersion is not null
            && !IsLoadingSharedPublicationCleanupPreview
            && !IsCleaningSharedPublication;
    }

    [RelayCommand(CanExecute = nameof(CanRefreshSharedPublicationCleanupPreview))]
    private async Task RefreshSharedPublicationCleanupPreviewAsync()
    {
        var publication = SelectedSharedPublicationVersion;
        if (publication is null)
        {
            return;
        }

        var request = BeginSharedPublicationCleanupRequest();
        var cancellationToken = request.Token;
        var requestVersion = ++sharedPublicationCleanupRequestVersion;
        IsLoadingSharedPublicationCleanupPreview = true;
        SharedPublicationCleanupMessage = T("data.shared_cleanup.loading_preview");
        SharedPublicationCleanupErrorMessage = null;
        try
        {
            var response = await _apiClient.GetSharedPublicationCleanupPreviewAsync(
                BuildSettings(),
                publication.PublicationId,
                cancellationToken);
            if (requestVersion != sharedPublicationCleanupRequestVersion
                || SelectedSharedPublicationVersion?.PublicationId
                != publication.PublicationId)
            {
                return;
            }

            if (response.Ok && response.Data is not null)
            {
                ApplySharedPublicationCleanupPreview(response.Data);
                return;
            }

            SharedPublicationCleanupMessage = T("data.shared_cleanup.preview_failed");
            SharedPublicationCleanupErrorMessage = DescribeError(response);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        finally
        {
            if (requestVersion == sharedPublicationCleanupRequestVersion)
            {
                IsLoadingSharedPublicationCleanupPreview = false;
            }

            CompleteSharedPublicationCleanupRequest(request);
        }
    }

    private bool CanCleanupSharedPublication()
    {
        return CanConfirmSharedPublicationCleanup;
    }

    [RelayCommand(CanExecute = nameof(CanCleanupSharedPublication))]
    private async Task CleanupSharedPublicationAsync()
    {
        var publication = SelectedSharedPublicationVersion;
        if (publication is null || SharedPublicationCleanupPreview is null)
        {
            return;
        }

        var request = BeginSharedPublicationCleanupRequest();
        var cancellationToken = request.Token;
        var requestVersion = ++sharedPublicationCleanupRequestVersion;
        IsCleaningSharedPublication = true;
        SharedPublicationCleanupMessage = T("data.shared_cleanup.cleaning");
        SharedPublicationCleanupErrorMessage = null;
        ApiResponseEnvelope<SharedPublicationCleanupResultDto>? response = null;
        try
        {
            response = await _apiClient.CleanupSharedPublicationAsync(
                BuildSettings(),
                publication.PublicationId,
                cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            return;
        }
        finally
        {
            if (requestVersion == sharedPublicationCleanupRequestVersion)
            {
                IsCleaningSharedPublication = false;
            }

            CompleteSharedPublicationCleanupRequest(request);
        }

        if (requestVersion != sharedPublicationCleanupRequestVersion
            || SelectedSharedPublicationVersion?.PublicationId
            != publication.PublicationId)
        {
            return;
        }

        if (response?.Ok != true || response.Data is null)
        {
            SharedPublicationCleanupMessage = T("data.shared_cleanup.cleanup_failed");
            SharedPublicationCleanupErrorMessage = response is null
                ? T("data.shared_cleanup.cleanup_failed")
                : DescribeError(response);
            return;
        }

        var resultMessage = response.Data.Outcome switch
        {
            "CLEANED" => T("data.shared_cleanup.result_cleaned"),
            "ALREADY_RELEASED" => T("data.shared_cleanup.result_already_released"),
            "BLOCKED" => T("data.shared_cleanup.result_blocked"),
            "RETRY_PENDING" => F(
                "format.shared_publication_cleanup_retry_pending",
                response.Data.RemainingMemberCount),
            "NOT_FOUND" => T("data.shared_cleanup.result_not_found"),
            _ => response.Data.Outcome,
        };
        if (response.Data.Blockers.Length > 0)
        {
            ApplySharedPublicationCleanupBlockers(response.Data.Blockers);
        }

        if (string.Equals(response.Data.Outcome, "BLOCKED", StringComparison.Ordinal))
        {
            await RefreshSharedPublicationCleanupPreviewAsync();
            SharedPublicationCleanupMessage = resultMessage;
            return;
        }

        await RefreshSharedPublicationVersionsAsync();
        SelectedSharedPublicationVersion = SharedPublicationVersions.FirstOrDefault(
            item => item.PublicationId == publication.PublicationId)
            ?? SelectedSharedPublicationVersion;
        await RefreshSharedPublicationCleanupPreviewAsync();
        SharedPublicationCleanupMessage = resultMessage;
    }

    private void ApplySharedPublicationCleanupPreview(
        SharedPublicationCleanupPreviewDto preview)
    {
        SharedPublicationCleanupPreview = preview;
        ApplySharedPublicationCleanupBlockers(preview.Blockers);
        SharedPublicationCleanupMessage = preview.Eligible
            ? T("data.shared_cleanup.preview_eligible")
            : T("data.shared_cleanup.preview_blocked");
    }

    private void ApplySharedPublicationCleanupBlockers(string[] blockers)
    {
        SharedPublicationCleanupBlockers.Clear();
        foreach (var blocker in blockers)
        {
            SharedPublicationCleanupBlockers.Add(
                T($"data.shared_cleanup.blocker.{blocker.ToLowerInvariant()}"));
        }

        OnPropertyChanged(nameof(HasSharedPublicationCleanupBlockers));
    }

    private CancellationTokenSource BeginSharedPublicationCleanupRequest()
    {
        CancelSharedPublicationCleanupRequest();
        sharedPublicationCleanupCancellation =
            CancellationTokenSource.CreateLinkedTokenSource(_shutdown.Token);
        return sharedPublicationCleanupCancellation;
    }

    private void CancelSharedPublicationCleanupRequest()
    {
        sharedPublicationCleanupRequestVersion++;
        sharedPublicationCleanupCancellation?.Cancel();
        sharedPublicationCleanupCancellation?.Dispose();
        sharedPublicationCleanupCancellation = null;
        IsLoadingSharedPublicationCleanupPreview = false;
        IsCleaningSharedPublication = false;
    }

    private void CompleteSharedPublicationCleanupRequest(CancellationTokenSource request)
    {
        if (ReferenceEquals(sharedPublicationCleanupCancellation, request))
        {
            sharedPublicationCleanupCancellation = null;
        }

        request.Dispose();
    }
}
