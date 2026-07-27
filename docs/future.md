# future features
1. upload failed should indicate that it failed. instead it currently says "uploading"
2. dev env should have its own priviledged AWS credentials: currently `.env.dev` is pointing to root user, which is a seciruty risk
3. Authentication
4. Orphaned S3 Multipart Upload Chunks: When a multipart upload is initiated but interrupted (and never completed or aborted), S3 retains those 50MB chunk files in hidden storage indefinitely.
5. 
