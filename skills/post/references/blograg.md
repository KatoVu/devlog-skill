# Publishing to BlogRAG

Only follow this when the author has explicitly asked to put the post on BlogRAG. "Write a post"
isn't that request. "Upload it to BlogRAG", "post it as a draft" and "publish it" are.

BlogRAG posts are also evidence in the author's recruiter-facing job-fit index once published. That's
why the connection only writes drafts, and why publishing waits for a separate, explicit yes.

## 0. Is the server connected?

Look for tools named like `mcp__blograg__create_draft`. If there aren't any, stop and tell the
author how to add it, then let them continue:

```
claude mcp add --transport http blograg https://mcp.blograg.pbh-dev.tech/mcp
```

On first use a browser opens so they can sign in and approve. The connection can create and edit
drafts, upload media, and publish when asked. It can never delete, edit a live post, or replace
existing artwork.

## 1. Preflight

1. `validate_post.py <folder>` passes with no errors.
2. `whoami`: confirm with the author that this is the right account if there's any doubt.
3. `list_posts` with `search` set to a few words from the title. If something similar exists,
   ask whether to continue with a new draft. (Drafts the author already has can be updated with
   `update_draft`. Published posts can't be touched from here.)

## 2. Create the draft

Call `create_draft` with `title`, `slug`, `summary`, `repo_url`/`demo_url` (only if set), and
`body` set to the post body **without the front matter**. For now, leave local embeds
(`![…](assets/x.png)`) as they are. They're replaced in step 4.

Record the returned `id` in the front matter as `blograg_post_id: <id>` so a later run updates
this draft instead of creating another.

## 3. Upload the artwork and every embedded file

For each file, call `request_upload` and then send the file to the URL it returns, **from the
post folder**:

```bash
curl -sS --fail-with-body -F "file=@assets/thumbnail.png" "<upload_url>"
```

| File | `role` | `caption` |
| --- | --- | --- |
| `assets/thumbnail.*` | `thumbnail` | what the picture shows |
| `assets/trailer.*` | `trailer` | what the video or picture shows |
| each `![alt](assets/…)` in the body | `attachment` | the embed's alt text |

The curl response is JSON for the stored file, and its `id` is what the body needs. An upload URL
works once and expires in minutes, so request it right before sending. If one fails, request a new
one. Don't retry the old one.

If the API says the draft **already has** a thumbnail or trailer, don't try to work around it.
The connection can't replace artwork. Tell the author to remove the old one in the studio if
they want the new one.

## 4. Point the body at the uploaded files

Replace each local embed with the uploaded file's path, keeping the alt text:

```
![The consent page listing what the app can do](assets/consent-page.png)
→ ![The consent page listing what the app can do](/api/media/42/content)
```

`list_media` returns the exact `markdown` for every file if you lost track. Then call
`update_draft` with the new body. Don't edit the local `post.md`: it stays the portable copy.

## 5. Check and report

Call `check_publish_readiness`. Tell the author the draft is up (title, id) and what, if anything,
is missing. They can review it in the BlogRAG studio.

## 6. Publish (only on a separate, explicit yes)

Only if the author says to publish: `publish_post` with `user_confirmed: true`. If they asked
for "upload" or "draft", don't publish and don't ask leading questions about it. Mention once
that it's ready when they are.

After publishing, the post can't be edited or unpublished from here. The author does that in
the studio.
