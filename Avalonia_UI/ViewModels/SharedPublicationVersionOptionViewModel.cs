using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class SharedPublicationVersionOptionViewModel
{
    public SharedPublicationVersionOptionViewModel(
        SharedPublicationSummaryDto summary)
    {
        PublicationId = summary.PublicationId;
        ShareName = summary.ShareName;
        PublicationVersion = summary.PublicationVersion;
        Status = summary.Status;
        MemberCount = summary.MemberCount;
        IsLatestPublished = summary.IsLatestPublished;
    }

    public string PublicationId { get; }

    public string ShareName { get; }

    public int PublicationVersion { get; }

    public string Status { get; }

    public int MemberCount { get; }

    public bool IsLatestPublished { get; }

    public bool IsPublished => Status == "PUBLISHED";

    public string DisplayText => $"v{PublicationVersion} / {Status} / {MemberCount}";
}
