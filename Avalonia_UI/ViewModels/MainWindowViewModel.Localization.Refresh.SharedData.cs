namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifySharedPublicationsLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(ShareText));
        OnPropertyChanged(nameof(ShareNameWatermarkText));
        OnPropertyChanged(nameof(VersionsText));
        OnPropertyChanged(nameof(SharedMemberLoadMoreText));
        OnPropertyChanged(nameof(SharedCleanupTitleText));
        OnPropertyChanged(nameof(SharedCleanupStatusLabelText));
        OnPropertyChanged(nameof(SharedCleanupExpiresAtLabelText));
        OnPropertyChanged(nameof(SharedCleanupRefreshPreviewText));
        OnPropertyChanged(nameof(SharedCleanupActionText));
        OnPropertyChanged(nameof(SharedCleanupConfirmText));
        OnPropertyChanged(nameof(SharedPublicationCleanupCountsText));
        if (SharedPublicationCleanupPreview is not null)
        {
            ApplySharedPublicationCleanupBlockers(
                SharedPublicationCleanupPreview.Blockers);
            SharedPublicationCleanupMessage = SharedPublicationCleanupPreview.Eligible
                ? T("data.shared_cleanup.preview_eligible")
                : T("data.shared_cleanup.preview_blocked");
        }
    }
}
