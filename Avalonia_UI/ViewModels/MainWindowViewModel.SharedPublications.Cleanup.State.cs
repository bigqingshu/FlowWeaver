using System.Collections.ObjectModel;
using System.Threading;
using Avalonia_UI.Api;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private CancellationTokenSource? sharedPublicationCleanupCancellation;
    private long sharedPublicationCleanupRequestVersion;

    [ObservableProperty]
    private bool isLoadingSharedPublicationCleanupPreview;

    [ObservableProperty]
    private bool isCleaningSharedPublication;

    [ObservableProperty]
    private SharedPublicationCleanupPreviewDto? sharedPublicationCleanupPreview;

    [ObservableProperty]
    private string sharedPublicationCleanupMessage = string.Empty;

    [ObservableProperty]
    private string? sharedPublicationCleanupErrorMessage;

    public ObservableCollection<string> SharedPublicationCleanupBlockers { get; } = new();

    public bool HasSharedPublicationCleanupError =>
        !string.IsNullOrWhiteSpace(SharedPublicationCleanupErrorMessage);

    public bool HasSharedPublicationCleanupPreview =>
        SharedPublicationCleanupPreview is not null;

    public bool HasSharedPublicationCleanupBlockers =>
        SharedPublicationCleanupBlockers.Count > 0;

    public bool IsSharedPublicationCleanupVisible =>
        SelectedSharedPublicationVersion is not null;

    public bool IsSharedPublicationCleanupBusy =>
        IsLoadingSharedPublicationCleanupPreview || IsCleaningSharedPublication;

    public bool CanConfirmSharedPublicationCleanup =>
        CanUseEngineActions
        && SelectedSharedPublicationVersion is not null
        && SharedPublicationCleanupPreview is not null
        && (SharedPublicationCleanupPreview.Eligible
            || string.Equals(
                SelectedSharedPublicationVersion.Status,
                "RELEASING",
                System.StringComparison.OrdinalIgnoreCase))
        && !IsLoadingSharedPublicationCleanupPreview
        && !IsCleaningSharedPublication;

    public string SharedPublicationCleanupStatusText =>
        SharedPublicationCleanupPreview?.Status
        ?? SelectedSharedPublicationVersion?.Status
        ?? "-";

    public string SharedPublicationCleanupExpiresAtText =>
        SharedPublicationCleanupPreview?.ExpiresAt?.ToLocalTime()
            .ToString("yyyy-MM-dd HH:mm:ss")
        ?? SelectedSharedPublicationVersion?.ExpiresAtText
        ?? "-";

    public string SharedPublicationCleanupCountsText =>
        SharedPublicationCleanupPreview is null
            ? string.Empty
            : F(
                "format.shared_publication_cleanup_counts",
                SharedPublicationCleanupPreview.ReleasableMemberCount,
                SharedPublicationCleanupPreview.ProtectedMemberCount,
                SharedPublicationCleanupPreview.ActiveReadLeaseCount,
                SharedPublicationCleanupPreview.ActiveTableLeaseCount);

    partial void OnSharedPublicationCleanupErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationCleanupError));
    }

    partial void OnSharedPublicationCleanupPreviewChanged(
        SharedPublicationCleanupPreviewDto? value)
    {
        OnPropertyChanged(nameof(HasSharedPublicationCleanupPreview));
        OnPropertyChanged(nameof(SharedPublicationCleanupStatusText));
        OnPropertyChanged(nameof(SharedPublicationCleanupExpiresAtText));
        OnPropertyChanged(nameof(SharedPublicationCleanupCountsText));
        OnPropertyChanged(nameof(CanConfirmSharedPublicationCleanup));
        CleanupSharedPublicationCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsLoadingSharedPublicationCleanupPreviewChanged(bool value)
    {
        OnPropertyChanged(nameof(IsSharedPublicationCleanupBusy));
        OnPropertyChanged(nameof(CanConfirmSharedPublicationCleanup));
        RefreshSharedPublicationCleanupPreviewCommand.NotifyCanExecuteChanged();
        CleanupSharedPublicationCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsCleaningSharedPublicationChanged(bool value)
    {
        OnPropertyChanged(nameof(IsSharedPublicationCleanupBusy));
        OnPropertyChanged(nameof(CanConfirmSharedPublicationCleanup));
        RefreshSharedPublicationCleanupPreviewCommand.NotifyCanExecuteChanged();
        CleanupSharedPublicationCommand.NotifyCanExecuteChanged();
    }

    private void ResetSharedPublicationCleanupState()
    {
        SharedPublicationCleanupPreview = null;
        SharedPublicationCleanupBlockers.Clear();
        SharedPublicationCleanupMessage = string.Empty;
        SharedPublicationCleanupErrorMessage = null;
        OnPropertyChanged(nameof(HasSharedPublicationCleanupBlockers));
        OnPropertyChanged(nameof(IsSharedPublicationCleanupVisible));
        OnPropertyChanged(nameof(CanConfirmSharedPublicationCleanup));
        RefreshSharedPublicationCleanupPreviewCommand.NotifyCanExecuteChanged();
        CleanupSharedPublicationCommand.NotifyCanExecuteChanged();
    }
}
